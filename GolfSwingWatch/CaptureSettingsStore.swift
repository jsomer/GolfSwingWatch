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

    @Published var bufferCapacity: Int {
        didSet {
            let clamped = Self.clamp(bufferCapacity)
            if clamped != bufferCapacity {
                bufferCapacity = clamped
                return
            }
            UserDefaults.standard.set(clamped, forKey: Self.bufferCapacityKey)
        }
    }

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

    func asPayload() -> [String: Any] {
        [
            "type": "captureSettings",
            "bufferCapacity": bufferCapacity,
        ]
    }
}
