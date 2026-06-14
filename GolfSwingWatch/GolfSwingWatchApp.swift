//
//  GolfSwingWatchApp.swift
//  GolfSwingWatch
//
//  Created by JohnSomerville on 6/10/26.
//

import SwiftUI
import SwiftData

@main
struct GolfSwingWatchApp: App {
    init() {
        PhoneSyncService.shared.activate()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(for: [StoredSwingRecord.self, StoredSwingSample.self])
    }
}
