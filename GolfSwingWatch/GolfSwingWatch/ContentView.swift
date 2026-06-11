import SwiftUI
import SwiftData

struct ContentView: View {
    @Query(sort: \StoredSwingRecord.date, order: .reverse) private var records: [StoredSwingRecord]
    private let similarityScorer = SwingSimilarityScorer()
    private let coach = CoachingEngine()

    var body: some View {
        NavigationStack {
            List {
                if records.isEmpty {
                    Text("No swings saved yet on iPhone.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(Array(records.enumerated()), id: \.element.id) { index, record in
                        let domain = record.asDomain()
                        NavigationLink {
                            SessionDetailView(
                                record: domain,
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
                }
            }
            .navigationTitle("Sessions")
        }
    }
}

private struct SessionDetailView: View {
    let record: SwingRecord
    let previousRecord: SwingRecord?
    let similarityScorer: SwingSimilarityScorer
    let coach: CoachingEngine

    var body: some View {
        List {
            Section("Summary") {
                Text("Club: \(record.club)")
                Text("Rating: \(record.rating)/5")
                Text("Samples: \(record.samples.count)")
                Text("Recorded: \(record.date.formatted())")
                if !record.notes.isEmpty {
                    Text("Notes: \(record.notes)")
                }
            }

            Section("Analytics") {
                Text("Tempo Ratio: \(record.analytics.tempoRatio, specifier: "%.2f")")
                Text("Peak Rotation: \(record.analytics.peakRotationalVelocity, specifier: "%.2f")")
                Text("Avg Accel: \(record.analytics.averageAcceleration, specifier: "%.2f")")
                Text("Plane Stability: \(record.analytics.swingPlaneStability, specifier: "%.2f")")
                Text("Confidence: \(record.analytics.confidence, specifier: "%.2f")")
            }

            if let previousRecord {
                Section("Comparison") {
                    let similarity = similarityScorer.score(
                        lhs: record.analytics,
                        rhs: previousRecord.analytics
                    )
                    Text("Similarity to previous swing: \(similarity, specifier: "%.2f")")
                }
            }

            Section("Coaching") {
                let generated = coach.recommendations(for: record.analytics, rating: record.rating)
                let allTips = Array(Set(record.recommendations + generated))
                ForEach(allTips, id: \.self) { tip in
                    Text(tip)
                }
            }
        }
        .navigationTitle("Swing Detail")
    }
}

#Preview {
    ContentView()
}
