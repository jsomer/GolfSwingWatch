import Foundation

struct SwingDetector {
    private var hasStarted = false
    private var sawImpact = false
    private var startTimestamp: Double?
    private var impactTimestamp: Double?

    mutating func reset() {
        hasStarted = false
        sawImpact = false
        startTimestamp = nil
        impactTimestamp = nil
    }

    mutating func process(sample: SwingSample) -> SwingEventType? {
        let gyroMagnitude = magnitude(sample.gyroX, sample.gyroY, sample.gyroZ)
        let accelMagnitude = magnitude(sample.accelX, sample.accelY, sample.accelZ)

        if !hasStarted && gyroMagnitude > 3.2 {
            hasStarted = true
            startTimestamp = sample.timestamp
            return .start
        }

        if hasStarted && !sawImpact && accelMagnitude > 2.4 {
            sawImpact = true
            impactTimestamp = sample.timestamp
            return .impact
        }

        if sawImpact,
           let impactTimestamp,
           sample.timestamp - impactTimestamp > 0.2,
           gyroMagnitude < 2.0 {
            reset()
            return .followThrough
        }

        return nil
    }

    private func magnitude(_ x: Double, _ y: Double, _ z: Double) -> Double {
        sqrt((x * x) + (y * y) + (z * z))
    }
}
