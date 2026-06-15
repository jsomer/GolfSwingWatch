import Foundation
import SwiftData

struct SwingSample: Codable, Hashable {
    let timestamp: Double
    let accelX: Double
    let accelY: Double
    let accelZ: Double
    let gyroX: Double
    let gyroY: Double
    let gyroZ: Double
    let pitch: Double
    let roll: Double
    let yaw: Double
}

enum SwingEventType: String, Codable, CaseIterable {
    case start
    case impact
    case followThrough
}

struct SwingEventMarker: Codable, Hashable {
    let timestamp: Double
    let type: SwingEventType
}

struct SwingAnalytics: Codable, Hashable {
    let tempoRatio: Double
    let peakRotationalVelocity: Double
    let averageAcceleration: Double
    let swingPlaneStability: Double
    let confidence: Double
}

struct SwingRecord: Identifiable, Codable, Hashable {
    let id: UUID
    let date: Date
    let rating: Int
    let club: String
    let notes: String
    let samples: [SwingSample]
    let eventMarkers: [SwingEventMarker]
    let analytics: SwingAnalytics
    let recommendations: [String]
    let swingMode: SwingMode
    let detectedEvents: [DetectedSwingEvent]
    let confirmedEvents: [DetectedSwingEvent]
    let flawTags: [String]
    let analysisVersion: String?

    init(
        id: UUID,
        date: Date,
        rating: Int,
        club: String,
        notes: String,
        samples: [SwingSample],
        eventMarkers: [SwingEventMarker],
        analytics: SwingAnalytics,
        recommendations: [String],
        swingMode: SwingMode = .practice,
        detectedEvents: [DetectedSwingEvent] = [],
        confirmedEvents: [DetectedSwingEvent] = [],
        flawTags: [String] = [],
        analysisVersion: String? = nil
    ) {
        self.id = id
        self.date = date
        self.rating = rating
        self.club = club
        self.notes = notes
        self.samples = samples
        self.eventMarkers = eventMarkers
        self.analytics = analytics
        self.recommendations = recommendations
        self.swingMode = swingMode
        self.detectedEvents = detectedEvents
        self.confirmedEvents = confirmedEvents
        self.flawTags = flawTags
        self.analysisVersion = analysisVersion
    }

    enum CodingKeys: String, CodingKey {
        case id
        case date
        case rating
        case club
        case notes
        case samples
        case eventMarkers
        case analytics
        case recommendations
        case swingMode
        case detectedEvents
        case confirmedEvents
        case flawTags
        case analysisVersion
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        date = try container.decode(Date.self, forKey: .date)
        rating = try container.decode(Int.self, forKey: .rating)
        club = try container.decode(String.self, forKey: .club)
        notes = try container.decode(String.self, forKey: .notes)
        samples = try container.decode([SwingSample].self, forKey: .samples)
        eventMarkers = try container.decodeIfPresent([SwingEventMarker].self, forKey: .eventMarkers) ?? []
        analytics = try container.decode(SwingAnalytics.self, forKey: .analytics)
        recommendations = try container.decodeIfPresent([String].self, forKey: .recommendations) ?? []
        swingMode = try container.decodeIfPresent(SwingMode.self, forKey: .swingMode) ?? .practice
        detectedEvents = try container.decodeIfPresent([DetectedSwingEvent].self, forKey: .detectedEvents) ?? []
        confirmedEvents = try container.decodeIfPresent([DetectedSwingEvent].self, forKey: .confirmedEvents) ?? []
        flawTags = try container.decodeIfPresent([String].self, forKey: .flawTags) ?? []
        analysisVersion = try container.decodeIfPresent(String.self, forKey: .analysisVersion)
    }

    var effectiveEvents: [DetectedSwingEvent] {
        confirmedEvents.isEmpty ? detectedEvents : confirmedEvents
    }
}

@Model
final class StoredSwingRecord {
    @Attribute(.unique) var id: UUID
    var date: Date
    var rating: Int
    var club: String
    var notes: String
    var eventMarkersData: Data
    var analyticsData: Data
    var recommendationsData: Data
    var swingModeRaw: String = SwingMode.practice.rawValue
    var detectedEventsData: Data = Data()
    var confirmedEventsData: Data = Data()
    var flawTagsData: Data = Data()
    var analysisVersion: String?
    @Relationship(deleteRule: .cascade, inverse: \StoredSwingSample.record)
    var samples: [StoredSwingSample]

    init(record: SwingRecord) {
        self.id = record.id
        self.date = record.date
        self.rating = record.rating
        self.club = record.club
        self.notes = record.notes
        self.eventMarkersData = Self.encode(record.eventMarkers)
        self.analyticsData = Self.encode(record.analytics)
        self.recommendationsData = Self.encode(record.recommendations)
        self.swingModeRaw = record.swingMode.rawValue
        self.detectedEventsData = Self.encode(record.detectedEvents)
        self.confirmedEventsData = Self.encode(record.confirmedEvents)
        self.flawTagsData = Self.encode(record.flawTags)
        self.analysisVersion = record.analysisVersion
        self.samples = record.samples.map { StoredSwingSample(sample: $0) }
        self.samples.forEach { $0.record = self }
    }

    func update(from record: SwingRecord) {
        date = record.date
        rating = record.rating
        club = record.club
        notes = record.notes
        eventMarkersData = Self.encode(record.eventMarkers)
        analyticsData = Self.encode(record.analytics)
        recommendationsData = Self.encode(record.recommendations)
        swingModeRaw = record.swingMode.rawValue
        detectedEventsData = Self.encode(record.detectedEvents)
        confirmedEventsData = Self.encode(record.confirmedEvents)
        flawTagsData = Self.encode(record.flawTags)
        analysisVersion = record.analysisVersion
        samples.removeAll()
        samples = record.samples.map { StoredSwingSample(sample: $0) }
        samples.forEach { $0.record = self }
    }

    func asDomain() -> SwingRecord {
        SwingRecord(
            id: id,
            date: date,
            rating: rating,
            club: club,
            notes: notes,
            samples: samples.sorted { $0.timestamp < $1.timestamp }.map(\.asDomain),
            eventMarkers: Self.decode(eventMarkersData, fallback: []),
            analytics: Self.decode(
                analyticsData,
                fallback: SwingAnalytics(
                    tempoRatio: 1,
                    peakRotationalVelocity: 0,
                    averageAcceleration: 0,
                    swingPlaneStability: 0,
                    confidence: 0
                )
            ),
            recommendations: Self.decode(recommendationsData, fallback: []),
            swingMode: SwingMode(rawValue: swingModeRaw) ?? .practice,
            detectedEvents: Self.decode(detectedEventsData, fallback: []),
            confirmedEvents: Self.decode(confirmedEventsData, fallback: []),
            flawTags: Self.decode(flawTagsData, fallback: []),
            analysisVersion: analysisVersion
        )
    }

    private static func encode<T: Encodable>(_ value: T) -> Data {
        (try? JSONEncoder().encode(value)) ?? Data()
    }

    private static func decode<T: Decodable>(_ data: Data, fallback: T) -> T {
        (try? JSONDecoder().decode(T.self, from: data)) ?? fallback
    }
}

@Model
final class StoredSwingSample {
    var timestamp: Double
    var accelX: Double
    var accelY: Double
    var accelZ: Double
    var gyroX: Double
    var gyroY: Double
    var gyroZ: Double
    var pitch: Double
    var roll: Double
    var yaw: Double
    var record: StoredSwingRecord?

    init(sample: SwingSample) {
        timestamp = sample.timestamp
        accelX = sample.accelX
        accelY = sample.accelY
        accelZ = sample.accelZ
        gyroX = sample.gyroX
        gyroY = sample.gyroY
        gyroZ = sample.gyroZ
        pitch = sample.pitch
        roll = sample.roll
        yaw = sample.yaw
    }

    var asDomain: SwingSample {
        SwingSample(
            timestamp: timestamp,
            accelX: accelX,
            accelY: accelY,
            accelZ: accelZ,
            gyroX: gyroX,
            gyroY: gyroY,
            gyroZ: gyroZ,
            pitch: pitch,
            roll: roll,
            yaw: yaw
        )
    }
}
