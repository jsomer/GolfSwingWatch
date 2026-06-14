//
//  GolfSwingWatchApp.swift
//  GolfSwingWatch Watch App
//
//  Created by JohnSomerville on 6/10/26.
//

import SwiftUI
import SwiftData

@main
struct GolfSwingWatch_Watch_AppApp: App {
    init() {
        WatchSyncService.shared.activate()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(for: [StoredSwingRecord.self, StoredSwingSample.self])
    }
}
