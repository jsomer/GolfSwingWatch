import Foundation
import SwiftData

@MainActor
final class SwingRepository {
    private let modelContext: ModelContext

    init(modelContext: ModelContext) {
        self.modelContext = modelContext
    }

    func save(record: SwingRecord) throws {
        let descriptor = FetchDescriptor<StoredSwingRecord>(
            predicate: #Predicate { $0.id == record.id }
        )
        if let existing = try modelContext.fetch(descriptor).first {
            existing.update(from: record)
        } else {
            modelContext.insert(StoredSwingRecord(record: record))
        }
        try modelContext.save()
    }

    func fetchAll() throws -> [SwingRecord] {
        var descriptor = FetchDescriptor<StoredSwingRecord>()
        descriptor.sortBy = [SortDescriptor(\.date, order: .reverse)]
        return try modelContext.fetch(descriptor).map { $0.asDomain() }
    }
}
