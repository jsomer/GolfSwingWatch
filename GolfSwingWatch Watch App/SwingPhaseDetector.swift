import Foundation

enum SwingMode: String, Codable, CaseIterable {
    case practice
    case full
}

struct DetectedSwingEvent: Codable, Hashable, Identifiable {
    var id: String { "\(type)-\(timestamp)" }
    let timestamp: Double
    let type: String
    let confidence: Double
    let source: String

    init(timestamp: Double, type: String, confidence: Double, source: String = "rule") {
        self.timestamp = timestamp
        self.type = type
        self.confidence = min(1, max(0, confidence))
        self.source = source
    }
}

struct SwingPhaseAnalysis: Codable, Hashable {
    let analysisVersion: String
    let swingMode: SwingMode
    let detectedEvents: [DetectedSwingEvent]
    let faultFlags: [String]
    let phaseChainComplete: Bool

    static let empty = SwingPhaseAnalysis(
        analysisVersion: SwingPhaseDetector.analysisVersion,
        swingMode: .practice,
        detectedEvents: [],
        faultFlags: [],
        phaseChainComplete: false
    )
}

enum SwingFlawTag: String, CaseIterable, Identifiable {
    case rushedTransition = "rushed_transition"
    case excessiveWristRoll = "excessive_wrist_roll"
    case midSwingPause = "mid_swing_pause"
    case incompleteFinish = "incomplete_finish"

    var id: String { rawValue }

    var label: String {
        switch self {
        case .rushedTransition: return "Rushed transition"
        case .excessiveWristRoll: return "Excessive wrist roll"
        case .midSwingPause: return "Mid-swing pause"
        case .incompleteFinish: return "Incomplete finish"
        }
    }
}

struct SwingPhaseDetector {
    static let analysisVersion = "event_finder_v1"

    private static let stillGyro = 2.0
    private static let takeawayGyro = 2.8
    private static let finishGyro = 2.0
    private static let contactAccel = 2.2
    private static let contactConfidenceMin = 0.35
    private static let rushedTransitionRatio = 0.55
    private static let pauseGyro = 1.8
    private static let pauseMinSamples = 2

    private static let phaseOrder = ["address", "takeaway", "top", "downswingStart", "finish"]

    static func analyze(
        samples: [SwingSample],
        legacyMarkers: [SwingEventMarker] = []
    ) -> SwingPhaseAnalysis {
        guard !samples.isEmpty else { return .empty }

        let ordered = samples.sorted { $0.timestamp < $1.timestamp }
        let gyroMag = ordered.map { magnitude($0.gyroX, $0.gyroY, $0.gyroZ) }
        let accelMag = ordered.map { magnitude($0.accelX, $0.accelY, $0.accelZ) }
        let timestamps = ordered.map(\.timestamp)

        let addressIndex = findAddressIndex(gyroMag)
        let takeawayIndex = findTakeawayIndex(gyroMag, startIndex: addressIndex)
        var topIndex = findTopIndex(gyroMag, takeawayIndex: takeawayIndex)
        if topIndex <= takeawayIndex {
            topIndex = min(takeawayIndex + 1, ordered.count - 1)
        }
        let downswingIndex = findDownswingStartIndex(gyroMag, topIndex: topIndex)
        let finishIndex = findFinishIndex(gyroMag, downswingIndex: downswingIndex)

        var events = [
            DetectedSwingEvent(timestamp: timestamps[addressIndex], type: "address", confidence: 0.8),
            DetectedSwingEvent(timestamp: timestamps[takeawayIndex], type: "takeaway", confidence: 0.85),
            DetectedSwingEvent(timestamp: timestamps[topIndex], type: "top", confidence: 0.8),
            DetectedSwingEvent(timestamp: timestamps[downswingIndex], type: "downswingStart", confidence: 0.75),
            DetectedSwingEvent(timestamp: timestamps[finishIndex], type: "finish", confidence: 0.8),
        ]

        if let contact = findContactGuess(
            timestamps: timestamps,
            accelMag: accelMag,
            downswingIndex: downswingIndex,
            finishIndex: finishIndex
        ) {
            events.append(contact)
        }

        events = mergeLegacyEvents(events, legacyMarkers: legacyMarkers)
        let eventMap = Dictionary(uniqueKeysWithValues: events.map { ($0.type, $0.timestamp) })
        let phaseChainComplete = phaseOrder.allSatisfy { eventMap[$0] != nil }
        let swingMode: SwingMode = eventMap["contactGuess"] != nil ? .full : .practice
        let faultFlags = faultFlags(
            eventMap: eventMap,
            gyroMag: gyroMag,
            takeawayIndex: takeawayIndex,
            topIndex: topIndex
        )

        return SwingPhaseAnalysis(
            analysisVersion: analysisVersion,
            swingMode: swingMode,
            detectedEvents: events.sorted { $0.timestamp < $1.timestamp },
            faultFlags: faultFlags,
            phaseChainComplete: phaseChainComplete
        )
    }

    private static func magnitude(_ x: Double, _ y: Double, _ z: Double) -> Double {
        sqrt((x * x) + (y * y) + (z * z))
    }

    private static func findAddressIndex(_ gyroMag: [Double]) -> Int {
        guard !gyroMag.isEmpty else { return 0 }
        var run = 0
        var bestEnd = 0
        for (index, value) in gyroMag.enumerated() {
            if value < stillGyro {
                run += 1
                if run >= pauseMinSamples {
                    bestEnd = index
                }
            } else {
                run = 0
            }
        }
        if bestEnd > 0 {
            return max(0, bestEnd - run + 1)
        }
        return 0
    }

    private static func findTakeawayIndex(_ gyroMag: [Double], startIndex: Int) -> Int {
        let start = max(startIndex, 0)
        for index in start..<gyroMag.count {
            if index + 1 >= gyroMag.count { break }
            if gyroMag[index] >= takeawayGyro && gyroMag[index + 1] >= takeawayGyro {
                return index
            }
        }
        let peakIndex = gyroMag.enumerated().max(by: { $0.element < $1.element })?.offset ?? start
        return min(max(start + 1, 0), peakIndex)
    }

    private static func findTopIndex(_ gyroMag: [Double], takeawayIndex: Int) -> Int {
        guard takeawayIndex < gyroMag.count - 2 else { return max(takeawayIndex, 0) }
        let searchEnd = min(max(takeawayIndex + 2, Int(Double(gyroMag.count) * 0.85)), gyroMag.count)
        let segment = Array(gyroMag[takeawayIndex..<searchEnd])
        guard !segment.isEmpty else { return takeawayIndex }
        let localMin = segment.enumerated().min(by: { $0.element < $1.element })?.offset ?? 0
        return takeawayIndex + localMin
    }

    private static func findDownswingStartIndex(_ gyroMag: [Double], topIndex: Int) -> Int {
        guard topIndex < gyroMag.count - 2 else { return topIndex }
        for index in (topIndex + 1)..<(gyroMag.count - 1) {
            if gyroMag[index + 1] > gyroMag[index] && gyroMag[index + 1] >= takeawayGyro {
                return index + 1
            }
        }
        let slice = gyroMag[topIndex...]
        let localPeak = slice.enumerated().max(by: { $0.element < $1.element })?.offset ?? 0
        return max(topIndex + 1, min(topIndex + localPeak, gyroMag.count - 1))
    }

    private static func findFinishIndex(_ gyroMag: [Double], downswingIndex: Int) -> Int {
        guard downswingIndex < gyroMag.count - 1 else { return gyroMag.count - 1 }
        let slice = gyroMag[downswingIndex...]
        let peakOffset = slice.enumerated().max(by: { $0.element < $1.element })?.offset ?? 0
        let peakIndex = downswingIndex + peakOffset
        for index in peakIndex..<gyroMag.count {
            if index + 1 >= gyroMag.count { return gyroMag.count - 1 }
            if gyroMag[index] < finishGyro && gyroMag[index + 1] < finishGyro {
                return index + 1
            }
        }
        return gyroMag.count - 1
    }

    private static func findContactGuess(
        timestamps: [Double],
        accelMag: [Double],
        downswingIndex: Int,
        finishIndex: Int
    ) -> DetectedSwingEvent? {
        guard finishIndex > downswingIndex else { return nil }
        let windowAccel = Array(accelMag[downswingIndex...finishIndex])
        guard let localPeak = windowAccel.enumerated().max(by: { $0.element < $1.element }) else { return nil }
        let peak = localPeak.element
        guard peak >= contactAccel else { return nil }
        let baseline = windowAccel.sorted()[windowAccel.count / 2]
        let confidence = peak > 0 ? (peak - baseline) / peak : 0
        guard confidence >= contactConfidenceMin else { return nil }
        let peakIndex = downswingIndex + localPeak.offset
        return DetectedSwingEvent(
            timestamp: timestamps[peakIndex],
            type: "contactGuess",
            confidence: confidence,
            source: "contactGuess"
        )
    }

    private static func mergeLegacyEvents(
        _ events: [DetectedSwingEvent],
        legacyMarkers: [SwingEventMarker]
    ) -> [DetectedSwingEvent] {
        let mapped: [SwingEventType: String] = [
            .start: "takeaway",
            .impact: "contactGuess",
            .followThrough: "finish",
        ]
        var existing = Dictionary(uniqueKeysWithValues: events.map { ($0.type, $0) })
        for marker in legacyMarkers {
            guard let phaseType = mapped[marker.type] else { continue }
            if let current = existing[phaseType], current.confidence >= 0.6 {
                continue
            }
            let confidence = marker.type == .impact ? 0.5 : 0.75
            existing[phaseType] = DetectedSwingEvent(
                timestamp: marker.timestamp,
                type: phaseType,
                confidence: confidence,
                source: "legacy"
            )
        }
        var ordered: [DetectedSwingEvent] = []
        for phaseType in phaseOrder + ["contactGuess"] {
            if let event = existing[phaseType] {
                ordered.append(event)
            }
        }
        for event in existing.values where !ordered.contains(where: { $0.type == event.type }) {
            ordered.append(event)
        }
        return ordered.sorted { $0.timestamp < $1.timestamp }
    }

    private static func faultFlags(
        eventMap: [String: Double],
        gyroMag: [Double],
        takeawayIndex: Int,
        topIndex: Int
    ) -> [String] {
        var flags: [String] = []
        if let backswing = span(eventMap, from: "takeaway", to: "top"),
           let downswing = span(eventMap, from: "top", to: "finish") ?? span(eventMap, from: "downswingStart", to: "finish"),
           downswing > 0 {
            let ratio = backswing / downswing
            if ratio < rushedTransitionRatio {
                flags.append(SwingFlawTag.rushedTransition.rawValue)
            }
        }
        if takeawayIndex < topIndex {
            let segment = Array(gyroMag[takeawayIndex..<topIndex])
            var pauseRun = 0
            for value in segment {
                if value < pauseGyro {
                    pauseRun += 1
                    if pauseRun >= pauseMinSamples {
                        flags.append(SwingFlawTag.midSwingPause.rawValue)
                        break
                    }
                } else {
                    pauseRun = 0
                }
            }
        }
        if eventMap["finish"] == nil {
            flags.append(SwingFlawTag.incompleteFinish.rawValue)
        }
        return flags
    }

    private static func span(_ eventMap: [String: Double], from startKey: String, to endKey: String) -> Double? {
        guard let start = eventMap[startKey], let end = eventMap[endKey], end > start else { return nil }
        return end - start
    }
}
