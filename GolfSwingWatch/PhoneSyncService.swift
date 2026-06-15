import Combine
import Foundation
import SwiftData
import WatchConnectivity

@MainActor
final class PhoneSyncService: NSObject, ObservableObject {
    static let shared = PhoneSyncService()

    @Published private(set) var statusMessage = "Waiting for watch swings..."
    @Published private(set) var lastImportedCount = 0
    @Published var captureSettings = CaptureSettingsStore.shared

    private var modelContext: ModelContext?
    private var pendingFileURL: URL?
    private var settingsCancellable: AnyCancellable?

    private override init() {
        super.init()
        settingsCancellable = Publishers.Merge(
            captureSettings.$bufferCapacity.map { _ in () },
            captureSettings.$sampleRateHz.map { _ in () }
        )
        .dropFirst()
        .sink { [weak self] _ in
            self?.pushCaptureSettingsToWatch()
        }
    }

    func activate() {
        guard WCSession.isSupported() else {
            statusMessage = "WatchConnectivity unavailable"
            return
        }

        let session = WCSession.default
        session.delegate = self
        session.activate()
        pushCaptureSettingsToWatch()
    }

    func pushCaptureSettingsToWatch() {
        guard WCSession.isSupported() else { return }
        guard WCSession.default.activationState == .activated else { return }

        do {
            try WCSession.default.updateApplicationContext(captureSettings.asPayload())
            if statusMessage.hasPrefix("Waiting for watch swings") || statusMessage == "Ready to receive watch swings" {
                statusMessage = "Watch capture settings updated"
            }
        } catch {
            statusMessage = "Failed to sync watch settings: \(error.localizedDescription)"
        }
    }

    func configure(modelContext: ModelContext) {
        self.modelContext = modelContext
        if let pendingFileURL {
            importRecords(from: pendingFileURL)
            self.pendingFileURL = nil
        }
    }

    private func importRecords(from url: URL) {
        guard let modelContext else {
            pendingFileURL = url
            statusMessage = "Queued watch import until app is ready"
            return
        }

        do {
            let records = try SwingExporter.readRecords(from: url)
            let repository = SwingRepository(modelContext: modelContext)
            for record in records {
                let normalized = SwingTimestampNormalization.normalizeRecord(
                    record,
                    reanalyzePhases: record.detectedEvents.isEmpty
                )
                try repository.save(record: normalized)
            }
            lastImportedCount = records.count
            statusMessage = "Imported \(records.count) swing(s) from watch"
            acknowledgeImport(recordIds: records.map(\.id))
        } catch {
            statusMessage = "Import failed: \(error.localizedDescription)"
        }
    }

    private func acknowledgeImport(recordIds: [UUID]) {
        guard WCSession.default.activationState == .activated else { return }
        guard !recordIds.isEmpty else { return }

        let payload: [String: Any] = [
            "type": "syncAck",
            "recordIds": recordIds.map(\.uuidString).joined(separator: ","),
        ]

        WCSession.default.transferUserInfo(payload)

        if WCSession.default.isReachable {
            WCSession.default.sendMessage(payload, replyHandler: nil) { _ in }
        }
    }
}

extension PhoneSyncService: WCSessionDelegate {
    nonisolated func session(
        _ session: WCSession,
        activationDidCompleteWith activationState: WCSessionActivationState,
        error: Error?
    ) {
        Task { @MainActor in
            if let error {
                statusMessage = "Sync error: \(error.localizedDescription)"
            } else if activationState == .activated {
                statusMessage = "Ready to receive watch swings"
                pushCaptureSettingsToWatch()
            }
        }
    }

    nonisolated func session(_ session: WCSession, didReceive file: WCSessionFile) {
        let receivedURL = file.fileURL
        Task { @MainActor in
            importRecords(from: receivedURL)
        }
    }

    nonisolated func sessionDidBecomeInactive(_ session: WCSession) {}

    nonisolated func sessionDidDeactivate(_ session: WCSession) {
        session.activate()
    }
}
