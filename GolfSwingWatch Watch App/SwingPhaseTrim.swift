import Foundation

enum SwingPhaseTrim {
    static let maxDurationSeconds = 8.0
    static let prePadSeconds = 0.15
    static let postPadSeconds = 0.25

    struct TrimmedSwing {
        let samples: [SwingSample]
        let markers: [SwingEventMarker]
        let detectedEvents: [DetectedSwingEvent]
    }

    static func trim(
        samples: [SwingSample],
        markers: [SwingEventMarker],
        detectedEvents: [DetectedSwingEvent]
    ) -> TrimmedSwing {
        let ordered = samples.sorted { $0.timestamp < $1.timestamp }
        guard let first = ordered.first, let last = ordered.last else {
            return TrimmedSwing(samples: [], markers: [], detectedEvents: [])
        }

        let sampleStart = first.timestamp
        let sampleEnd = last.timestamp
        let window = phaseWindow(
            events: detectedEvents,
            sampleStart: sampleStart,
            sampleEnd: sampleEnd
        ) ?? activeWindowWithCap(samples: ordered, sampleStart: sampleStart, sampleEnd: sampleEnd)

        return applyWindow(
            samples: ordered,
            markers: markers,
            detectedEvents: detectedEvents,
            windowStart: window.start,
            windowEnd: window.end
        )
    }

    private struct TimeWindow {
        let start: Double
        let end: Double
    }

    private static func eventTime(_ events: [DetectedSwingEvent], types: [String]) -> Double? {
        for type in types {
            if let event = events.first(where: { $0.type == type }) {
                return event.timestamp
            }
        }
        return nil
    }

    private static func phaseWindow(
        events: [DetectedSwingEvent],
        sampleStart: Double,
        sampleEnd: Double
    ) -> TimeWindow? {
        guard let phaseStart = eventTime(events, types: ["address", "takeaway", "start"]),
              let phaseEnd = eventTime(events, types: ["finish", "followThrough"]),
              phaseEnd > phaseStart else {
            return nil
        }
        let start = max(sampleStart, phaseStart - prePadSeconds)
        let end = min(sampleEnd, phaseEnd + postPadSeconds)
        return capWindow(
            windowStart: start,
            windowEnd: end,
            coreStart: phaseStart,
            coreEnd: phaseEnd,
            sampleStart: sampleStart,
            sampleEnd: sampleEnd
        )
    }

    private static func activeWindowWithCap(
        samples: [SwingSample],
        sampleStart: Double,
        sampleEnd: Double
    ) -> TimeWindow {
        let peakSample = samples.max {
            magnitude($0.gyroX, $0.gyroY, $0.gyroZ) < magnitude($1.gyroX, $1.gyroY, $1.gyroZ)
        } ?? samples[samples.count / 2]
        let core = peakSample.timestamp
        return capWindow(
            windowStart: sampleStart,
            windowEnd: sampleEnd,
            coreStart: core,
            coreEnd: core,
            sampleStart: sampleStart,
            sampleEnd: sampleEnd
        )
    }

    private static func capWindow(
        windowStart: Double,
        windowEnd: Double,
        coreStart: Double,
        coreEnd: Double,
        sampleStart: Double,
        sampleEnd: Double
    ) -> TimeWindow {
        var start = windowStart
        var end = windowEnd
        if end - start <= maxDurationSeconds {
            return TimeWindow(start: start, end: end)
        }
        let center = (coreStart + coreEnd) / 2.0
        let half = maxDurationSeconds / 2.0
        start = max(sampleStart, center - half)
        end = min(sampleEnd, center + half)
        if end - start > maxDurationSeconds {
            end = start + maxDurationSeconds
        }
        if end - start < maxDurationSeconds, end < sampleEnd {
            end = min(sampleEnd, start + maxDurationSeconds)
        }
        return TimeWindow(start: start, end: end)
    }

    private static func applyWindow(
        samples: [SwingSample],
        markers: [SwingEventMarker],
        detectedEvents: [DetectedSwingEvent],
        windowStart: Double,
        windowEnd: Double
    ) -> TrimmedSwing {
        let clipped = samples.filter { $0.timestamp >= windowStart && $0.timestamp <= windowEnd }
        guard let base = clipped.first?.timestamp else {
            return TrimmedSwing(samples: [], markers: [], detectedEvents: [])
        }

        let rebasedSamples = clipped.map { sample in
            SwingSample(
                timestamp: sample.timestamp - base,
                accelX: sample.accelX,
                accelY: sample.accelY,
                accelZ: sample.accelZ,
                gyroX: sample.gyroX,
                gyroY: sample.gyroY,
                gyroZ: sample.gyroZ,
                pitch: sample.pitch,
                roll: sample.roll,
                yaw: sample.yaw
            )
        }

        let rebasedMarkers = markers.compactMap { marker -> SwingEventMarker? in
            guard marker.timestamp >= windowStart, marker.timestamp <= windowEnd else { return nil }
            return SwingEventMarker(timestamp: marker.timestamp - base, type: marker.type)
        }

        let rebasedEvents = detectedEvents.compactMap { event -> DetectedSwingEvent? in
            guard event.timestamp >= windowStart, event.timestamp <= windowEnd else { return nil }
            return DetectedSwingEvent(
                timestamp: event.timestamp - base,
                type: event.type,
                confidence: event.confidence,
                source: event.source
            )
        }

        return TrimmedSwing(
            samples: rebasedSamples,
            markers: rebasedMarkers,
            detectedEvents: rebasedEvents
        )
    }

    private static func magnitude(_ x: Double, _ y: Double, _ z: Double) -> Double {
        sqrt((x * x) + (y * y) + (z * z))
    }
}
