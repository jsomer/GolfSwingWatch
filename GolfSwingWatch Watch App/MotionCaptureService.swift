import CoreMotion
import Foundation

@MainActor
final class MotionCaptureService {
    private let motionManager: CMMotionManager
    private let queue: OperationQueue
    private(set) var isRunning = false

    var onSample: ((SwingSample) -> Void)?

    init(motionManager: CMMotionManager = CMMotionManager()) {
        self.motionManager = motionManager
        self.queue = OperationQueue()
        self.queue.name = "golfswing.motion.capture"
        self.queue.maxConcurrentOperationCount = 1
    }

    func start(sampleRateHz: Double = 50) throws {
        guard motionManager.isDeviceMotionAvailable else {
            throw NSError(
                domain: "GolfSwingWatch.MotionCapture",
                code: 1,
                userInfo: [NSLocalizedDescriptionKey: "Device motion is unavailable on this watch."]
            )
        }

        motionManager.deviceMotionUpdateInterval = 1.0 / sampleRateHz
        motionManager.startDeviceMotionUpdates(to: queue) { [weak self] motion, _ in
            guard let motion else { return }
            let sample = SwingSample(
                timestamp: motion.timestamp,
                accelX: motion.userAcceleration.x,
                accelY: motion.userAcceleration.y,
                accelZ: motion.userAcceleration.z,
                gyroX: motion.rotationRate.x,
                gyroY: motion.rotationRate.y,
                gyroZ: motion.rotationRate.z,
                pitch: motion.attitude.pitch,
                roll: motion.attitude.roll,
                yaw: motion.attitude.yaw
            )

            Task { @MainActor in
                self?.onSample?(sample)
            }
        }

        isRunning = true
    }

    func stop() {
        motionManager.stopDeviceMotionUpdates()
        isRunning = false
    }
}
