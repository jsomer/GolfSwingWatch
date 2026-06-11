import Foundation
import Combine
import SwiftData

@MainActor
final class SessionViewModel: ObservableObject {
    enum SessionState: String {
        case idle
        case recording
        case saving
        case error
    }

    @Published private(set) var state: SessionState = .idle
    @Published private(set) var sampleCount = 0
    @Published private(set) var lastError: String?
    @Published private(set) var lastAnalytics: SwingAnalytics?
    @Published private(set) var lastRecommendations: [String] = []
    @Published private(set) var latestSimilarityScore: Double?

    private let captureService: MotionCaptureService
    private let extractor = SwingFeatureExtractor()
    private let coach = CoachingEngine()
    private let scorer = SwingSimilarityScorer()
    private var detector = SwingDetector()
    private var ringBuffer = RingBuffer<SwingSample>(capacity: 1000)
    private var eventMarkers: [SwingEventMarker] = []
    private var latestSavedRecord: SwingRecord?

    init(captureService: MotionCaptureService? = nil) {
        self.captureService = captureService ?? MotionCaptureService()
        self.captureService.onSample = { [weak self] sample in
            self?.handleIncoming(sample: sample)
        }
    }

    func startSession() {
        do {
            resetSessionBuffers()
            try captureService.start()
            state = .recording
            lastError = nil
        } catch {
            state = .error
            lastError = error.localizedDescription
        }
    }

    func stopSession() {
        captureService.stop()
        if state != .error {
            state = .idle
        }
    }

    func saveSwing(
        modelContext: ModelContext,
        rating: Int,
        club: String,
        notes: String
    ) {
        let samples = ringBuffer.snapshot()
        guard !samples.isEmpty else {
            state = .error
            lastError = "No samples recorded. Start a session first."
            return
        }

        state = .saving
        let analytics = extractor.extract(samples: samples, markers: eventMarkers)
        let recommendations = coach.recommendations(for: analytics, rating: rating)
        let record = SwingRecord(
            id: UUID(),
            date: Date(),
            rating: rating,
            club: club,
            notes: notes,
            samples: samples,
            eventMarkers: eventMarkers,
            analytics: analytics,
            recommendations: recommendations
        )

        do {
            let repository = SwingRepository(modelContext: modelContext)
            try repository.save(record: record)
            latestSimilarityScore = latestSavedRecord.map {
                scorer.score(lhs: analytics, rhs: $0.analytics)
            }
            latestSavedRecord = record
            lastAnalytics = analytics
            lastRecommendations = recommendations
            state = .idle
            lastError = nil
        } catch {
            state = .error
            lastError = "Failed to save swing: \(error.localizedDescription)"
        }
    }

    private func handleIncoming(sample: SwingSample) {
        guard state == .recording else { return }
        ringBuffer.append(sample)
        sampleCount = ringBuffer.count
        if let eventType = detector.process(sample: sample) {
            eventMarkers.append(SwingEventMarker(timestamp: sample.timestamp, type: eventType))
        }
    }

    private func resetSessionBuffers() {
        ringBuffer.clear()
        detector.reset()
        eventMarkers.removeAll()
        sampleCount = 0
    }
}
