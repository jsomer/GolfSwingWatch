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
            samples: samples
                .sorted { $0.timestamp < $1.timestamp }
                .map(\.asDomain),
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
            recommendations: Self.decode(recommendationsData, fallback: [])
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
