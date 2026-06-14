import Combine
import Foundation

@MainActor
final class CaptureSettingsStore: ObservableObject {
    static let shared = CaptureSettingsStore()

    static let minBufferCapacity = 500
    static let maxBufferCapacity = 10_000
    static let defaultBufferCapacity = 3_000
    static let sampleRateHz = 50.0

    private static let bufferCapacityKey = "captureBufferCapacity"

    @Published private(set) var bufferCapacity: Int

    private init() {
        let stored = UserDefaults.standard.integer(forKey: Self.bufferCapacityKey)
        if stored == 0 {
            bufferCapacity = Self.defaultBufferCapacity
        } else {
            bufferCapacity = Self.clamp(stored)
        }
    }

    static func clamp(_ value: Int) -> Int {
        min(max(value, minBufferCapacity), maxBufferCapacity)
    }

    static func estimatedSeconds(for capacity: Int) -> Double {
        Double(capacity) / sampleRateHz
    }

    func apply(bufferCapacity newValue: Int) {
        let clamped = Self.clamp(newValue)
        guard clamped != bufferCapacity else { return }
        bufferCapacity = clamped
        UserDefaults.standard.set(clamped, forKey: Self.bufferCapacityKey)
    }

    func apply(payload: [String: Any]) {
        guard payload["type"] as? String == "captureSettings" else { return }
        guard let rawCapacity = payload["bufferCapacity"] as? Int else { return }
        apply(bufferCapacity: rawCapacity)
    }

    func asPayload() -> [String: Any] {
        [
            "type": "captureSettings",
            "bufferCapacity": bufferCapacity,
        ]
    }
}
