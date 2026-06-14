import Combine
import Foundation
import SwiftData
import WatchConnectivity

@MainActor
final class WatchSyncService: NSObject, ObservableObject {
    static let shared = WatchSyncService()

    @Published private(set) var statusMessage = "Sync idle"
    @Published private(set) var isSending = false
    @Published var autoDeleteAfterSync: Bool {
        didSet {
            UserDefaults.standard.set(autoDeleteAfterSync, forKey: Self.autoDeleteKey)
        }
    }

    private static let autoDeleteKey = "autoDeleteAfterSync"

    private var modelContext: ModelContext?

    private override init() {
        if UserDefaults.standard.object(forKey: Self.autoDeleteKey) == nil {
            UserDefaults.standard.set(true, forKey: Self.autoDeleteKey)
        }
        autoDeleteAfterSync = UserDefaults.standard.bool(forKey: Self.autoDeleteKey)
        super.init()
    }

    func activate() {
        guard WCSession.isSupported() else {
            statusMessage = "WatchConnectivity unavailable"
            return
        }

        let session = WCSession.default
        session.delegate = self
        session.activate()
        applyCaptureSettings(from: session.receivedApplicationContext)
    }

    func configure(modelContext: ModelContext) {
        self.modelContext = modelContext
    }

    func sendRecords(_ records: [SwingRecord]) {
        guard !records.isEmpty else {
            statusMessage = "No swings to send"
            return
        }
        guard !isSending else { return }

        let session = WCSession.default
        guard session.activationState == .activated else {
            statusMessage = "Sync not ready — open iPhone app once"
            return
        }
        guard session.isCompanionAppInstalled else {
            statusMessage = "Install iPhone app first"
            return
        }

        isSending = true
        statusMessage = "Preparing \(records.count) swing(s)..."

        Task {
            await sendPreparedRecords(records)
        }
    }

    func sendAll(_ storedRecords: [StoredSwingRecord]) {
        sendRecords(storedRecords.map { $0.asDomain() })
    }

    private func sendPreparedRecords(_ records: [SwingRecord]) async {
        do {
            let url = try await Task.detached(priority: .userInitiated) {
                try SwingExporter.writeExportFile(
                    from: records,
                    filename: SwingExporter.exportFilename,
                    prettyPrint: false
                )
            }.value

            let recordIds = records.map(\.id.uuidString).joined(separator: ",")
            WCSession.default.transferFile(
                url,
                metadata: [
                    "type": "swingExport",
                    "recordIds": recordIds,
                ]
            )
            statusMessage = "Queued \(records.count) swing(s) for iPhone"
        } catch {
            statusMessage = "Send failed: \(error.localizedDescription)"
            isSending = false
        }
    }

    private func applyCaptureSettings(from payload: [String: Any]) {
        guard !payload.isEmpty else { return }
        CaptureSettingsStore.shared.apply(payload: payload)
    }

    private func handleSyncAck(_ payload: [String: Any]) {
        guard payload["type"] as? String == "syncAck" else { return }

        let ids = Self.parseRecordIds(payload["recordIds"])
        guard !ids.isEmpty else { return }

        guard autoDeleteAfterSync else {
            statusMessage = "iPhone saved \(ids.count) swing(s)"
            return
        }

        guard let modelContext else {
            statusMessage = "Synced \(ids.count) swing(s); open app to clear watch storage"
            return
        }

        let repository = SwingRepository(modelContext: modelContext)
        var removed = 0
        for id in ids {
            do {
                try repository.delete(id: id)
                removed += 1
            } catch {
                continue
            }
        }

        if removed > 0 {
            statusMessage = "Removed \(removed) synced swing(s) from watch"
        } else {
            statusMessage = "iPhone saved \(ids.count) swing(s)"
        }
    }

    private static func parseRecordIds(_ value: Any?) -> [UUID] {
        if let joined = value as? String {
            return joined
                .split(separator: ",")
                .compactMap { UUID(uuidString: String($0)) }
        }
        if let array = value as? [String] {
            return array.compactMap { UUID(uuidString: $0) }
        }
        return []
    }
}

extension WatchSyncService: WCSessionDelegate {
    nonisolated func session(
        _ session: WCSession,
        activationDidCompleteWith activationState: WCSessionActivationState,
        error: Error?
    ) {
        Task { @MainActor in
            if let error {
                statusMessage = "Sync error: \(error.localizedDescription)"
            } else if activationState == .activated {
                applyCaptureSettings(from: session.receivedApplicationContext)
                if session.isCompanionAppInstalled {
                    statusMessage = "Ready to sync with iPhone"
                } else {
                    statusMessage = "Install iPhone app to sync"
                }
            }
        }
    }

    nonisolated func sessionReachabilityDidChange(_ session: WCSession) {
        Task { @MainActor in
            guard session.activationState == .activated, !isSending else { return }
            if session.isReachable {
                statusMessage = "iPhone reachable — ready to sync"
            } else if session.isCompanionAppInstalled {
                statusMessage = "Ready to sync (iPhone nearby)"
            }
        }
    }

    nonisolated func session(_ session: WCSession, didFinish fileTransfer: WCSessionFileTransfer, error: Error?) {
        Task { @MainActor in
            if let error {
                statusMessage = "Transfer failed: \(error.localizedDescription)"
                isSending = false
            } else {
                statusMessage = "Sent to iPhone — waiting for save confirmation"
            }
        }
    }

    nonisolated func session(_ session: WCSession, didReceiveUserInfo userInfo: [String: Any] = [:]) {
        Task { @MainActor in
            handleSyncAck(userInfo)
            isSending = false
        }
    }

    nonisolated func session(_ session: WCSession, didReceiveApplicationContext applicationContext: [String: Any]) {
        Task { @MainActor in
            applyCaptureSettings(from: applicationContext)
        }
    }

    nonisolated func session(_ session: WCSession, didReceiveMessage message: [String: Any]) {
        Task { @MainActor in
            handleSyncAck(message)
            isSending = false
        }
    }
}
