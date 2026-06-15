import Foundation

enum SwingTimestampNormalization {
    static let phaseDisplayOrder = [
        "address",
        "takeaway",
        "top",
        "downswingStart",
        "contactGuess",
        "finish",
    ]

    static func origin(for samples: [SwingSample]) -> Double {
        samples.map(\.timestamp).min() ?? 0
    }

    static func swingDuration(for samples: [SwingSample]) -> Double {
        guard !samples.isEmpty else { return 0 }
        let sorted = samples.sorted { $0.timestamp < $1.timestamp }
        return max((sorted.last?.timestamp ?? 0) - (sorted.first?.timestamp ?? 0), 0.01)
    }

    static func needsNormalization(for record: SwingRecord) -> Bool {
        let origin = origin(for: record.samples)
        guard origin > 0.01 else { return false }
        let duration = swingDuration(for: record.samples)
        let events = record.confirmedEvents.isEmpty ? record.detectedEvents : record.confirmedEvents
        if events.contains(where: { $0.timestamp > duration + 1 }) {
            return true
        }
        return record.eventMarkers.contains(where: { $0.timestamp > duration + 1 })
    }

    static func normalize(samples: [SwingSample], origin: Double) -> [SwingSample] {
        samples
            .sorted { $0.timestamp < $1.timestamp }
            .map { sample in
                SwingSample(
                    timestamp: sample.timestamp - origin,
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
    }

    static func normalize(markers: [SwingEventMarker], origin: Double) -> [SwingEventMarker] {
        markers.map { marker in
            SwingEventMarker(timestamp: marker.timestamp - origin, type: marker.type)
        }
    }

    static func normalize(events: [DetectedSwingEvent], origin: Double) -> [DetectedSwingEvent] {
        events.map { event in
            DetectedSwingEvent(
                timestamp: event.timestamp - origin,
                type: event.type,
                confidence: event.confidence,
                source: event.source
            )
        }
    }

    static func sortedForDisplay(_ events: [DetectedSwingEvent]) -> [DetectedSwingEvent] {
        events.sorted { lhs, rhs in
            let leftIndex = phaseDisplayOrder.firstIndex(of: lhs.type) ?? phaseDisplayOrder.count
            let rightIndex = phaseDisplayOrder.firstIndex(of: rhs.type) ?? phaseDisplayOrder.count
            if leftIndex == rightIndex {
                return lhs.timestamp < rhs.timestamp
            }
            return leftIndex < rightIndex
        }
    }

    static func normalizeRecord(_ record: SwingRecord, reanalyzePhases: Bool = false) -> SwingRecord {
        let origin = origin(for: record.samples)
        guard origin > 0.01 || reanalyzePhases else { return record }

        let normalizedSamples = normalize(samples: record.samples, origin: origin)
        let normalizedMarkers = normalize(markers: record.eventMarkers, origin: origin)
        let normalizedDetected = normalize(events: record.detectedEvents, origin: origin)
        let normalizedConfirmed = normalize(events: record.confirmedEvents, origin: origin)

        let analysis: SwingPhaseAnalysis
        if reanalyzePhases || normalizedDetected.isEmpty {
            analysis = SwingPhaseDetector.analyze(
                samples: normalizedSamples,
                legacyMarkers: normalizedMarkers
            )
        } else {
            analysis = SwingPhaseAnalysis(
                analysisVersion: record.analysisVersion ?? SwingPhaseDetector.analysisVersion,
                swingMode: record.swingMode,
                detectedEvents: normalizedDetected,
                faultFlags: record.flawTags,
                phaseChainComplete: !normalizedDetected.isEmpty
            )
        }

        return SwingRecord(
            id: record.id,
            date: record.date,
            rating: record.rating,
            club: record.club,
            notes: record.notes,
            samples: normalizedSamples,
            eventMarkers: normalizedMarkers,
            analytics: record.analytics,
            recommendations: record.recommendations,
            swingMode: analysis.swingMode,
            detectedEvents: analysis.detectedEvents,
            confirmedEvents: normalizedConfirmed,
            flawTags: record.flawTags.isEmpty ? analysis.faultFlags : record.flawTags,
            analysisVersion: analysis.analysisVersion
        )
    }
}
