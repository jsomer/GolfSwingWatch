# Data Model

## SwingSample

```swift
struct SwingSample {
    let timestamp: Double
    let accelX: Double
    let accelY: Double
    let accelZ: Double
    let gyroX: Double
    let gyroY: Double
    let gyroZ: Double
    let pitch: Double
    let roll: Double
    let yaw: Double
}
```

## SwingRecord

```swift
struct SwingRecord {
    let id: UUID
    let date: Date
    let rating: Int
    let club: String
    let notes: String
    let samples: [SwingSample]
}
```
