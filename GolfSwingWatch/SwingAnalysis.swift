import Foundation

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
