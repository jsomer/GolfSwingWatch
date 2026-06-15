import SwiftUI
import SwiftData

struct ContentView: View {
    @Environment(\.modelContext) private var modelContext
    @Query(sort: \StoredSwingRecord.date, order: .reverse) private var records: [StoredSwingRecord]
    @ObservedObject private var syncService = PhoneSyncService.shared
    @ObservedObject private var captureSettings = CaptureSettingsStore.shared
    @State private var exportURL: URL?
    @State private var showExportError = false
    @State private var exportError = ""
    @State private var showDeleteAllConfirmation = false
    private let similarityScorer = SwingSimilarityScorer()
    private let coach = CoachingEngine()

    var body: some View {
        NavigationStack {
            List {
                Section("Watch Sync") {
                    Text(syncService.statusMessage)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Section("Watch Capture") {
                    Stepper(
                        value: $captureSettings.bufferCapacity,
                        in: CaptureSettingsStore.minBufferCapacity...CaptureSettingsStore.maxBufferCapacity,
                        step: 500
                    ) {
                        Text("Buffer: \(captureSettings.bufferCapacity) samples")
                    }
                    Stepper(
                        value: $captureSettings.sampleRateHz,
                        in: CaptureSettingsStore.minSampleRateHz...CaptureSettingsStore.maxSampleRateHz,
                        step: CaptureSettingsStore.sampleRateStepHz
                    ) {
                        Text("Sample rate: \(Int(captureSettings.sampleRateHz)) Hz")
                    }
                    Text(
                        "About \(captureSettings.estimatedSeconds(for: captureSettings.bufferCapacity), specifier: "%.0f") seconds at \(Int(captureSettings.sampleRateHz)) Hz. When full, oldest samples roll off until you save."
                    )
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    Button("Send settings to watch") {
                        syncService.pushCaptureSettingsToWatch()
                    }
                }

                if records.isEmpty {
                    Text("No swings saved yet on iPhone.")
                        .foregroundStyle(.secondary)
                } else {
                    Section {
                        Button("Delete All Swings", role: .destructive) {
                            showDeleteAllConfirmation = true
                        }
                    }

                    ForEach(Array(records.enumerated()), id: \.element.id) { index, record in
                        let domain = record.asDomain()
                        NavigationLink {
                            SessionDetailView(
                                record: domain,
                                recordID: record.id,
                                previousRecord: index + 1 < records.count ? records[index + 1].asDomain() : nil,
                                similarityScorer: similarityScorer,
                                coach: coach
                            )
                        } label: {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(record.club)
                                    .font(.headline)
                                Text(record.date, style: .date)
                                    .font(.caption)
                                Text("Rating: \(record.rating) • Samples: \(record.samples.count)")
                                    .font(.caption2)
                            }
                        }
                    }
                    .onDelete(perform: deleteRecords)
                }
            }
            .navigationTitle("Sessions")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    if let exportURL {
                        ShareLink(item: exportURL, preview: SharePreview("Golf Swings Export")) {
                            Label("Share", systemImage: "square.and.arrow.up")
                        }
                    }
                }
                ToolbarItem(placement: .topBarLeading) {
                    Button("Export") {
                        prepareExport()
                    }
                    .disabled(records.isEmpty)
                }
            }
            .alert("Export Failed", isPresented: $showExportError) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(exportError)
            }
            .confirmationDialog(
                "Delete all \(records.count) swing(s)?",
                isPresented: $showDeleteAllConfirmation,
                titleVisibility: .visible
            ) {
                Button("Delete All", role: .destructive) {
                    deleteAllRecords()
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This cannot be undone.")
            }
            .onAppear {
                syncService.configure(modelContext: modelContext)
            }
        }
    }

    private func prepareExport() {
        do {
            let domainRecords = records.map { $0.asDomain() }
            exportURL = try SwingExporter.writeExportFile(from: domainRecords)
        } catch {
            exportURL = nil
            exportError = error.localizedDescription
            showExportError = true
        }
    }

    private func deleteRecords(at offsets: IndexSet) {
        let repository = SwingRepository(modelContext: modelContext)
        for index in offsets {
            let record = records[index]
            try? repository.delete(id: record.id)
        }
        if exportURL != nil {
            prepareExport()
        }
    }

    private func deleteAllRecords() {
        let repository = SwingRepository(modelContext: modelContext)
        try? repository.deleteAll()
        exportURL = nil
    }
}

private struct SessionDetailView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(\.dismiss) private var dismiss

    let recordID: UUID
    let previousRecord: SwingRecord?
    let similarityScorer: SwingSimilarityScorer
    let coach: CoachingEngine

    @State private var workingRecord: SwingRecord
    @State private var showDeleteConfirmation = false

    init(
        record: SwingRecord,
        recordID: UUID,
        previousRecord: SwingRecord?,
        similarityScorer: SwingSimilarityScorer,
        coach: CoachingEngine
    ) {
        self.recordID = recordID
        self.previousRecord = previousRecord
        self.similarityScorer = similarityScorer
        self.coach = coach
        _workingRecord = State(initialValue: record)
    }

    var body: some View {
        List {
            Section("Summary") {
                Text("Club: \(workingRecord.club)")
                Text("Rating: \(workingRecord.rating)/5")
                Text("Samples: \(workingRecord.samples.count)")
                Text("Recorded: \(workingRecord.date.formatted())")
                Text("Mode: \(workingRecord.swingMode.rawValue.capitalized)")
                if !workingRecord.notes.isEmpty {
                    Text("Notes: \(workingRecord.notes)")
                }
            }

            Section("Analytics") {
                Text("Tempo Ratio: \(workingRecord.analytics.tempoRatio, specifier: "%.2f")")
                Text("Peak Rotation: \(workingRecord.analytics.peakRotationalVelocity, specifier: "%.2f")")
                Text("Avg Accel: \(workingRecord.analytics.averageAcceleration, specifier: "%.2f")")
                Text("Plane Stability: \(workingRecord.analytics.swingPlaneStability, specifier: "%.2f")")
                Text("Confidence: \(workingRecord.analytics.confidence, specifier: "%.2f")")
            }

            SwingPhaseLabelView(record: workingRecord) { updated in
                persist(updated)
            }

            if let previousRecord {
                Section("Comparison") {
                    let similarity = similarityScorer.score(
                        lhs: workingRecord.analytics,
                        rhs: previousRecord.analytics
                    )
                    Text("Similarity to previous swing: \(similarity, specifier: "%.2f")")
                }
            }

            Section("Coaching") {
                let generated = coach.recommendations(for: workingRecord.analytics, rating: workingRecord.rating)
                let allTips = Array(Set(workingRecord.recommendations + generated))
                ForEach(allTips, id: \.self) { tip in
                    Text(tip)
                }
            }

            Section {
                Button("Delete Swing", role: .destructive) {
                    showDeleteConfirmation = true
                }
            }
        }
        .navigationTitle("Swing Detail")
        .onAppear {
            ensurePhaseAnalysis()
        }
        .confirmationDialog(
            "Delete this swing?",
            isPresented: $showDeleteConfirmation,
            titleVisibility: .visible
        ) {
            Button("Delete", role: .destructive) {
                deleteRecord()
            }
            Button("Cancel", role: .cancel) {}
        }
    }

    private func ensurePhaseAnalysis() {
        guard workingRecord.detectedEvents.isEmpty else { return }
        let analysis = SwingPhaseDetector.analyze(
            samples: workingRecord.samples,
            legacyMarkers: workingRecord.eventMarkers
        )
        let enriched = SwingRecord(
            id: workingRecord.id,
            date: workingRecord.date,
            rating: workingRecord.rating,
            club: workingRecord.club,
            notes: workingRecord.notes,
            samples: workingRecord.samples,
            eventMarkers: workingRecord.eventMarkers,
            analytics: workingRecord.analytics,
            recommendations: workingRecord.recommendations,
            swingMode: analysis.swingMode,
            detectedEvents: analysis.detectedEvents,
            confirmedEvents: workingRecord.confirmedEvents,
            flawTags: analysis.faultFlags,
            analysisVersion: analysis.analysisVersion
        )
        workingRecord = enriched
        persist(enriched)
    }

    private func persist(_ record: SwingRecord) {
        let repository = SwingRepository(modelContext: modelContext)
        try? repository.save(record: record)
        workingRecord = record
    }

    private func deleteRecord() {
        let repository = SwingRepository(modelContext: modelContext)
        try? repository.delete(id: recordID)
        dismiss()
    }
}

#Preview {
    ContentView()
}
