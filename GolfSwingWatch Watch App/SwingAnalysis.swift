import Foundation

struct SwingFeatureExtractor {
    func extract(samples: [SwingSample], markers: [SwingEventMarker]) -> SwingAnalytics {
        guard !samples.isEmpty else {
            return SwingAnalytics(
                tempoRatio: 1.0,
                peakRotationalVelocity: 0.0,
                averageAcceleration: 0.0,
                swingPlaneStability: 0.0,
                confidence: 0.0
            )
        }

        let peakRotationalVelocity = samples
            .map { magnitude($0.gyroX, $0.gyroY, $0.gyroZ) }
            .max() ?? 0

        let averageAcceleration = samples
            .map { magnitude($0.accelX, $0.accelY, $0.accelZ) }
            .reduce(0, +) / Double(samples.count)

        let rollValues = samples.map(\.roll)
        let swingPlaneStability = inverseStdDev(values: rollValues)

        let start = markers.first(where: { $0.type == .start })?.timestamp
        let impact = markers.first(where: { $0.type == .impact })?.timestamp
        let follow = markers.first(where: { $0.type == .followThrough })?.timestamp
        let tempoRatio = computeTempoRatio(start: start, impact: impact, follow: follow)

        let confidence = min(1.0, Double(samples.count) / 300.0)

        return SwingAnalytics(
            tempoRatio: tempoRatio,
            peakRotationalVelocity: peakRotationalVelocity,
            averageAcceleration: averageAcceleration,
            swingPlaneStability: swingPlaneStability,
            confidence: confidence
        )
    }

    private func computeTempoRatio(start: Double?, impact: Double?, follow: Double?) -> Double {
        guard let start, let impact, let follow else { return 1.0 }
        let backSwingDuration = max(impact - start, 0.001)
        let followDuration = max(follow - impact, 0.001)
        return backSwingDuration / followDuration
    }

    private func inverseStdDev(values: [Double]) -> Double {
        guard values.count > 1 else { return 1.0 }
        let mean = values.reduce(0, +) / Double(values.count)
        let variance = values
            .map { pow($0 - mean, 2) }
            .reduce(0, +) / Double(values.count)
        return 1.0 / (1.0 + sqrt(variance))
    }

    private func magnitude(_ x: Double, _ y: Double, _ z: Double) -> Double {
        sqrt((x * x) + (y * y) + (z * z))
    }
}

struct SwingSimilarityScorer {
    func score(lhs: SwingAnalytics, rhs: SwingAnalytics) -> Double {
        let tempoDelta = abs(lhs.tempoRatio - rhs.tempoRatio)
        let rotationDelta = abs(lhs.peakRotationalVelocity - rhs.peakRotationalVelocity) / 8.0
        let accelerationDelta = abs(lhs.averageAcceleration - rhs.averageAcceleration) / 3.0
        let planeDelta = abs(lhs.swingPlaneStability - rhs.swingPlaneStability)

        let weightedDelta = (tempoDelta * 0.35)
            + (rotationDelta * 0.3)
            + (accelerationDelta * 0.2)
            + (planeDelta * 0.15)
        return max(0, min(1, 1 - weightedDelta))
    }
}

struct CoachingEngine {
    func recommendations(for analytics: SwingAnalytics, rating: Int) -> [String] {
        var tips: [String] = []

        if analytics.tempoRatio > 3.5 {
            tips.append("Transition is rushed. Slow down from backswing to impact.")
        } else if analytics.tempoRatio < 2.2 {
            tips.append("Tempo is too even. Build more speed into impact.")
        }

        if analytics.swingPlaneStability < 0.55 {
            tips.append("Swing plane varies a lot. Focus on a repeatable takeaway.")
        }

        if analytics.peakRotationalVelocity < 3.0 {
            tips.append("Rotation speed is low. Drive hips through impact.")
        }

        if rating >= 4 {
            tips.append("Strong rep. Save this swing as a benchmark.")
        }

        return tips.isEmpty ? ["Consistent profile. Keep repeating this motion."] : tips
    }
}
