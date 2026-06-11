//
//  GolfSwingWatch_Watch_AppTests.swift
//  GolfSwingWatch Watch AppTests
//
//  Created by JohnSomerville on 6/10/26.
//

import Testing
@testable import GolfSwingWatch_Watch_App

struct GolfSwingWatch_Watch_AppTests {
    @Test func ringBufferOverwritesOldestEntry() {
        var buffer = RingBuffer<Int>(capacity: 3)
        buffer.append(1)
        buffer.append(2)
        buffer.append(3)
        buffer.append(4)

        #expect(buffer.count == 3)
        #expect(buffer.snapshot() == [2, 3, 4])
    }

    @Test func detectorFindsStartImpactAndFollowThrough() {
        var detector = SwingDetector()

        let start = detector.process(sample: sample(timestamp: 0.0, gx: 4.0, gy: 0, gz: 0, ax: 0, ay: 0, az: 0))
        let impact = detector.process(sample: sample(timestamp: 0.1, gx: 4.2, gy: 0, gz: 0, ax: 2.7, ay: 0, az: 0))
        let follow = detector.process(sample: sample(timestamp: 0.35, gx: 0.5, gy: 0, gz: 0, ax: 0.4, ay: 0, az: 0))

        #expect(start == .start)
        #expect(impact == .impact)
        #expect(follow == .followThrough)
    }

    @Test func featureExtractionReturnsConfidenceFromSampleCount() {
        let extractor = SwingFeatureExtractor()
        let samples = (0..<150).map { index in
            sample(
                timestamp: Double(index) * 0.02,
                gx: 1.0,
                gy: 0.5,
                gz: 0.2,
                ax: 0.8,
                ay: 0.3,
                az: 0.4
            )
        }
        let analytics = extractor.extract(samples: samples, markers: [])
        #expect(analytics.confidence > 0.45)
        #expect(analytics.confidence < 0.55)
    }

    private func sample(
        timestamp: Double,
        gx: Double,
        gy: Double,
        gz: Double,
        ax: Double,
        ay: Double,
        az: Double
    ) -> SwingSample {
        SwingSample(
            timestamp: timestamp,
            accelX: ax,
            accelY: ay,
            accelZ: az,
            gyroX: gx,
            gyroY: gy,
            gyroZ: gz,
            pitch: 0,
            roll: 0,
            yaw: 0
        )
    }
}
