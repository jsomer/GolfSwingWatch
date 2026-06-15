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

    @Published var sampleRateHz: Double {
        didSet {
            let clamped = Self.clampSampleRate(sampleRateHz)
            if clamped != sampleRateHz {
                sampleRateHz = clamped
                return
            }
            UserDefaults.standard.set(clamped, forKey: Self.sampleRateKey)
        }
    }

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

    func asPayload() -> [String: Any] {
        [
            "type": "captureSettings",
            "bufferCapacity": bufferCapacity,
            "sampleRateHz": sampleRateHz,
        ]
    }
}
