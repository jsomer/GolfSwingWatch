import SwiftUI
import SwiftData

struct ContentView: View {
    @Environment(\.modelContext) private var modelContext
    @Query(sort: \StoredSwingRecord.date, order: .reverse) private var savedRecords: [StoredSwingRecord]
    @StateObject private var viewModel = SessionViewModel()
    @State private var rating = 3
    @State private var club = "7I"
    @State private var notes = ""
    @ObservedObject private var syncService = WatchSyncService.shared

    var body: some View {
        ScrollView {
            VStack(spacing: 10) {
                Text("Golf Swing")
                    .font(.headline)

                Text(viewModel.state.rawValue.capitalized)
                    .font(.caption)
                    .foregroundStyle(viewModel.state == .error ? .red : .secondary)

                Text("Samples: \(viewModel.sampleCount)/\(viewModel.bufferCapacity)")
                    .font(.caption2)

                if viewModel.bufferIsFull {
                    Text("Buffer full — oldest samples rolling off")
                        .font(.caption2)
                        .foregroundStyle(.orange)
                }

                HStack {
                    Button("Start") {
                        viewModel.startSession()
                    }
                    .disabled(viewModel.state == .recording || viewModel.state == .saving)

                    Button("Stop") {
                        viewModel.stopSession()
                    }
                    .disabled(viewModel.state != .recording)
                }
                .buttonStyle(.borderedProminent)

                Stepper("Rating: \(rating)", value: $rating, in: 1...5)
                    .font(.caption2)

                TextField("Club", text: $club)
                TextField("Notes", text: $notes)

                Button("Save Swing") {
                    viewModel.saveSwing(
                        modelContext: modelContext,
                        rating: rating,
                        club: club,
                        notes: notes
                    )
                }
                .disabled(viewModel.sampleCount == 0 || viewModel.state == .saving || viewModel.state == .recording)

                if let analytics = viewModel.lastAnalytics {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Tempo \(analytics.tempoRatio, specifier: "%.2f")")
                        Text("Peak Rot \(analytics.peakRotationalVelocity, specifier: "%.2f")")
                        Text("Confidence \(analytics.confidence, specifier: "%.2f")")
                    }
                    .font(.caption2)
                }

                if let similarity = viewModel.latestSimilarityScore {
                    Text("Similarity to last: \(similarity, specifier: "%.2f")")
                        .font(.caption2)
                }

                if !viewModel.lastRecommendations.isEmpty {
                    VStack(alignment: .leading, spacing: 3) {
                        ForEach(viewModel.lastRecommendations, id: \.self) { tip in
                            Text("- \(tip)")
                        }
                    }
                    .font(.caption2)
                }

                if let lastError = viewModel.lastError {
                    Text(lastError)
                        .font(.caption2)
                        .foregroundStyle(.red)
                }

                Divider()

                Text("Saved swings: \(savedRecords.count)")
                    .font(.caption2)

                Toggle("Remove after iPhone sync", isOn: $syncService.autoDeleteAfterSync)
                    .font(.caption2)

                if !savedRecords.isEmpty {
                    ForEach(savedRecords) { record in
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(record.club)
                                    .font(.caption)
                                Text(record.date, style: .date)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            Button(role: .destructive) {
                                deleteRecord(record)
                            } label: {
                                Image(systemName: "trash")
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }

                Button("Send All to iPhone") {
                    syncService.sendAll(savedRecords)
                }
                .disabled(savedRecords.isEmpty || viewModel.state == .saving || syncService.isSending)

                Text(syncService.isSending ? "Sending..." : syncService.statusMessage)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            .padding()
        }
        .onAppear {
            syncService.activate()
            syncService.configure(modelContext: modelContext)
        }
    }

    private func deleteRecord(_ record: StoredSwingRecord) {
        let repository = SwingRepository(modelContext: modelContext)
        try? repository.delete(id: record.id)
    }
}

#Preview {
    ContentView()
}
