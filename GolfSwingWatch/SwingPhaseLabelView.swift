import SwiftUI

struct SwingPhaseLabelView: View {
    let record: SwingRecord
    let onSave: (SwingRecord) -> Void

    @State private var editableEvents: [DetectedSwingEvent]
    @State private var selectedFlawTags: Set<String>
    @State private var swingMode: SwingMode
    @State private var hasEdits = false

    private var duration: Double {
        SwingTimestampNormalization.swingDuration(for: record.samples)
    }

    init(record: SwingRecord, onSave: @escaping (SwingRecord) -> Void) {
        self.record = record
        self.onSave = onSave
        let baseline = record.confirmedEvents.isEmpty ? record.detectedEvents : record.confirmedEvents
        let sortedBaseline = SwingTimestampNormalization.sortedForDisplay(baseline)
        _editableEvents = State(initialValue: sortedBaseline)
        _selectedFlawTags = State(initialValue: Set(record.flawTags))
        _swingMode = State(initialValue: record.swingMode)
    }

    var body: some View {
        Section("Swing Phases") {
            Text("Times are seconds from the start of this swing clip.")
                .font(.caption)
                .foregroundStyle(.secondary)

            Picker("Mode", selection: $swingMode) {
                ForEach(SwingMode.allCases, id: \.self) { mode in
                    Text(mode.rawValue.capitalized).tag(mode)
                }
            }
            .onChange(of: swingMode) { _, _ in hasEdits = true }

            if editableEvents.isEmpty {
                Text("No phases detected yet.")
                    .foregroundStyle(.secondary)
                    .font(.caption)
            } else {
                ForEach(editableEvents.indices, id: \.self) { index in
                    phaseRow(at: index)
                }
            }

            Button("Reset to detected phases") {
                editableEvents = SwingTimestampNormalization.sortedForDisplay(record.detectedEvents)
                selectedFlawTags = Set(record.flawTags)
                swingMode = record.swingMode
                hasEdits = true
            }
            .disabled(record.detectedEvents.isEmpty)

            if hasEdits {
                Button("Save phase labels") {
                    saveLabels()
                }
            }
        }

        Section("Flaw Tags") {
            ForEach(SwingFlawTag.allCases) { tag in
                Toggle(tag.label, isOn: flawBinding(for: tag.rawValue))
            }
        }
    }

    private func phaseRow(at index: Int) -> some View {
        let event = editableEvents[index]
        return VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(phaseLabel(event.type))
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Text("\(event.timestamp, specifier: "%.2f")s")
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(.secondary)
            }
            Slider(
                value: Binding(
                    get: { editableEvents[index].timestamp },
                    set: { newValue in
                        editableEvents[index] = DetectedSwingEvent(
                            timestamp: min(max(newValue, 0), duration),
                            type: event.type,
                            confidence: 1.0,
                            source: "user"
                        )
                        hasEdits = true
                    }
                ),
                in: 0...duration,
                step: 0.01
            )
        }
        .padding(.vertical, 4)
    }

    private func flawBinding(for tag: String) -> Binding<Bool> {
        Binding(
            get: { selectedFlawTags.contains(tag) },
            set: { isSelected in
                if isSelected {
                    selectedFlawTags.insert(tag)
                } else {
                    selectedFlawTags.remove(tag)
                }
                hasEdits = true
            }
        )
    }

    private func phaseLabel(_ type: String) -> String {
        switch type {
        case "address": return "Address"
        case "takeaway": return "Takeaway"
        case "top": return "Top"
        case "downswingStart": return "Downswing start"
        case "contactGuess": return "Contact (guess)"
        case "finish": return "Finish"
        default: return type.capitalized
        }
    }

    private func saveLabels() {
        let updated = SwingRecord(
            id: record.id,
            date: record.date,
            rating: record.rating,
            club: record.club,
            notes: record.notes,
            samples: record.samples,
            eventMarkers: record.eventMarkers,
            analytics: record.analytics,
            recommendations: record.recommendations,
            swingMode: swingMode,
            detectedEvents: record.detectedEvents,
            confirmedEvents: SwingTimestampNormalization.sortedForDisplay(editableEvents),
            flawTags: Array(selectedFlawTags).sorted(),
            analysisVersion: record.analysisVersion ?? SwingPhaseDetector.analysisVersion
        )
        onSave(updated)
        hasEdits = false
    }
}
