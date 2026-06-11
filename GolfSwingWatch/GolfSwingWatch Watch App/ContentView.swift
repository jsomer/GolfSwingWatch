import SwiftUI
import SwiftData

struct ContentView: View {
    @Environment(\.modelContext) private var modelContext
    @StateObject private var viewModel = SessionViewModel()
    @State private var rating = 3
    @State private var club = "7I"
    @State private var notes = ""

    var body: some View {
        ScrollView {
            VStack(spacing: 10) {
                Text("Golf Swing")
                    .font(.headline)

                Text(viewModel.state.rawValue.capitalized)
                    .font(.caption)
                    .foregroundStyle(viewModel.state == .error ? .red : .secondary)

                Text("Samples: \(viewModel.sampleCount)")
                    .font(.caption2)

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
                .disabled(viewModel.sampleCount == 0 || viewModel.state == .saving)

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
            }
            .padding()
        }
    }
}

#Preview {
    ContentView()
}
