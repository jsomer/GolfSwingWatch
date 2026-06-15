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
    @Published private(set) var bufferCapacity: Int
    @Published private(set) var sampleRateHz: Double
    @Published private(set) var bufferIsFull = false
    @Published private(set) var lastError: String?
    @Published private(set) var lastAnalytics: SwingAnalytics?
    @Published private(set) var lastRecommendations: [String] = []
    @Published private(set) var latestSimilarityScore: Double?

    private let captureService: MotionCaptureService
    private let extractor = SwingFeatureExtractor()
    private let coach = CoachingEngine()
    private let scorer = SwingSimilarityScorer()
    private var detector = SwingDetector()
    private var ringBuffer: RingBuffer<SwingSample>
    private var eventMarkers: [SwingEventMarker] = []
    private var latestSavedRecord: SwingRecord?
    private var settingsCancellable: AnyCancellable?

    init(captureService: MotionCaptureService? = nil) {
        let settings = CaptureSettingsStore.shared
        let initialCapacity = settings.bufferCapacity
        self.bufferCapacity = initialCapacity
        self.sampleRateHz = settings.sampleRateHz
        self.ringBuffer = RingBuffer(capacity: initialCapacity)
        self.captureService = captureService ?? MotionCaptureService()
        self.captureService.onSample = { [weak self] sample in
            self?.handleIncoming(sample: sample)
        }

        settingsCancellable = Publishers.CombineLatest(
            CaptureSettingsStore.shared.$bufferCapacity,
            CaptureSettingsStore.shared.$sampleRateHz
        )
        .sink { [weak self] capacity, rate in
            self?.applyBufferCapacity(capacity)
            self?.applySampleRate(rate)
        }
    }

    func startSession() {
        do {
            resetSessionBuffers()
            try captureService.start(sampleRateHz: sampleRateHz)
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
        bufferIsFull = false
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
        guard state != .saving else { return }

        let resumeRecording = state == .recording
        let markers = eventMarkers
        state = .saving

        Task { @MainActor in
            await Task.yield()

            let analytics = extractor.extract(samples: samples, markers: markers)
            let recommendations = coach.recommendations(for: analytics, rating: rating)
            let phaseAnalysis = SwingPhaseDetector.analyze(samples: samples, legacyMarkers: markers)
            let record = SwingRecord(
                id: UUID(),
                date: Date(),
                rating: rating,
                club: club,
                notes: notes,
                samples: samples,
                eventMarkers: markers,
                analytics: analytics,
                recommendations: recommendations,
                swingMode: phaseAnalysis.swingMode,
                detectedEvents: phaseAnalysis.detectedEvents,
                flawTags: phaseAnalysis.faultFlags,
                analysisVersion: phaseAnalysis.analysisVersion
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
                if WatchSyncService.shared.autoSyncAfterSave {
                    WatchSyncService.shared.sendRecords([record])
                }
                resetSessionBuffers()

                if resumeRecording {
                    if !captureService.isRunning {
                        try captureService.start(sampleRateHz: sampleRateHz)
                    }
                    state = .recording
                } else {
                    captureService.stop()
                    state = .idle
                }
                lastError = nil
            } catch {
                captureService.stop()
                state = .error
                lastError = "Failed to save swing: \(error.localizedDescription)"
            }
        }
    }

    private func handleIncoming(sample: SwingSample) {
        guard state == .recording else { return }
        ringBuffer.append(sample)
        sampleCount = ringBuffer.count
        bufferIsFull = ringBuffer.isFull
        if let eventType = detector.process(sample: sample) {
            eventMarkers.append(SwingEventMarker(timestamp: sample.timestamp, type: eventType))
        }
    }

    private func applyBufferCapacity(_ capacity: Int) {
        bufferCapacity = capacity
        ringBuffer.resize(capacity: capacity)
        sampleCount = ringBuffer.count
        bufferIsFull = state == .recording && ringBuffer.isFull
    }

    private func applySampleRate(_ rate: Double) {
        sampleRateHz = rate
        guard state == .recording, captureService.isRunning else { return }
        captureService.stop()
        do {
            try captureService.start(sampleRateHz: rate)
            lastError = nil
        } catch {
            state = .error
            lastError = error.localizedDescription
        }
    }

    private func resetSessionBuffers() {
        ringBuffer.clear()
        detector.reset()
        eventMarkers.removeAll()
        sampleCount = 0
        bufferIsFull = false
    }
}
