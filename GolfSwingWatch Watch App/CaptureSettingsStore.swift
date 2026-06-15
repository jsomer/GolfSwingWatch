import Combine
import Foundation

@MainActor
final class CaptureSettingsStore: ObservableObject {
    static let shared = CaptureSettingsStore()

    static let minBufferCapacity = 500
    static let maxBufferCapacity = 10_000
    static let defaultBufferCapacity = 3_000

    static let minSampleRateHz = 50.0
    static let maxSampleRateHz = 100.0
    static let defaultSampleRateHz = 50.0
    static let sampleRateStepHz = 10.0

    private static let bufferCapacityKey = "captureBufferCapacity"
    private static let sampleRateKey = "captureSampleRateHz"

    @Published private(set) var bufferCapacity: Int
    @Published private(set) var sampleRateHz: Double

    private init() {
        let storedCapacity = UserDefaults.standard.integer(forKey: Self.bufferCapacityKey)
        if storedCapacity == 0 {
            bufferCapacity = Self.defaultBufferCapacity
        } else {
            bufferCapacity = Self.clamp(storedCapacity)
        }

        let storedRate = UserDefaults.standard.double(forKey: Self.sampleRateKey)
        if storedRate == 0 {
            sampleRateHz = Self.defaultSampleRateHz
        } else {
            sampleRateHz = Self.clampSampleRate(storedRate)
        }
    }

    static func clamp(_ value: Int) -> Int {
        min(max(value, minBufferCapacity), maxBufferCapacity)
    }

    static func clampSampleRate(_ value: Double) -> Double {
        let stepped = (value / sampleRateStepHz).rounded() * sampleRateStepHz
        return min(max(stepped, minSampleRateHz), maxSampleRateHz)
    }

    func estimatedSeconds(for capacity: Int) -> Double {
        Double(capacity) / sampleRateHz
    }

    func apply(bufferCapacity newValue: Int) {
        let clamped = Self.clamp(newValue)
        guard clamped != bufferCapacity else { return }
        bufferCapacity = clamped
        UserDefaults.standard.set(clamped, forKey: Self.bufferCapacityKey)
    }

    func apply(sampleRateHz newValue: Double) {
        let clamped = Self.clampSampleRate(newValue)
        guard clamped != sampleRateHz else { return }
        sampleRateHz = clamped
        UserDefaults.standard.set(clamped, forKey: Self.sampleRateKey)
    }

    func apply(payload: [String: Any]) {
        guard payload["type"] as? String == "captureSettings" else { return }
        if let rawCapacity = payload["bufferCapacity"] as? Int {
            apply(bufferCapacity: rawCapacity)
        }
        if let rawRate = payload["sampleRateHz"] as? Double {
            apply(sampleRateHz: rawRate)
        } else if let rawRate = payload["sampleRateHz"] as? Int {
            apply(sampleRateHz: Double(rawRate))
        }
    }

    func asPayload() -> [String: Any] {
        [
            "type": "captureSettings",
            "bufferCapacity": bufferCapacity,
            "sampleRateHz": sampleRateHz,
        ]
    }
}
