//
//  GolfSwingWatchTests.swift
//  GolfSwingWatchTests
//
//  Created by JohnSomerville on 6/10/26.
//

import Testing
@testable import GolfSwingWatch

struct GolfSwingWatchTests {
    @Test func similarityScoreIsHighForNearMatch() {
        let scorer = SwingSimilarityScorer()
        let lhs = SwingAnalytics(
            tempoRatio: 3.0,
            peakRotationalVelocity: 5.4,
            averageAcceleration: 1.8,
            swingPlaneStability: 0.72,
            confidence: 0.9
        )
        let rhs = SwingAnalytics(
            tempoRatio: 2.9,
            peakRotationalVelocity: 5.2,
            averageAcceleration: 1.7,
            swingPlaneStability: 0.69,
            confidence: 0.9
        )

        #expect(scorer.score(lhs: lhs, rhs: rhs) > 0.85)
    }

    @Test func coachingEngineProducesTargetedTips() {
        let engine = CoachingEngine()
        let analytics = SwingAnalytics(
            tempoRatio: 4.1,
            peakRotationalVelocity: 2.4,
            averageAcceleration: 1.2,
            swingPlaneStability: 0.4,
            confidence: 0.8
        )

        let tips = engine.recommendations(for: analytics, rating: 2)
        #expect(tips.contains { $0.contains("Transition is rushed") })
        #expect(tips.contains { $0.contains("Swing plane varies") })
        #expect(tips.contains { $0.contains("Rotation speed is low") })
    }
}
