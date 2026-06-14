import Foundation

enum SwingExporter {
    static let exportFilename = "golf_swings_export.json"

    enum ExportError: LocalizedError {
        case noRecords

        var errorDescription: String? {
            switch self {
            case .noRecords:
                return "No saved swings to export."
            }
        }
    }

    static func writeExportFile(
        from records: [SwingRecord],
        filename: String = exportFilename,
        prettyPrint: Bool = true
    ) throws -> URL {
        let data = try makeJSON(from: records, prettyPrint: prettyPrint)
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(filename)
        if FileManager.default.fileExists(atPath: url.path) {
            try FileManager.default.removeItem(at: url)
        }
        try data.write(to: url, options: .atomic)
        return url
    }

    static func makeJSON(from records: [SwingRecord], prettyPrint: Bool = true) throws -> Data {
        guard !records.isEmpty else {
            throw ExportError.noRecords
        }

        let encoder = JSONEncoder()
        if prettyPrint {
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        }
        encoder.dateEncodingStrategy = .iso8601
        return try encoder.encode(records)
    }

    static func readRecords(from url: URL) throws -> [SwingRecord] {
        let data = try Data(contentsOf: url)
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode([SwingRecord].self, from: data)
    }
}
