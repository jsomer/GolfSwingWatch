import Foundation

struct RingBuffer<Element> {
    private var storage: [Element?]
    private(set) var count = 0
    private var writeIndex = 0

    private(set) var capacity: Int

    init(capacity: Int) {
        self.capacity = max(capacity, 1)
        self.storage = Array(repeating: nil, count: self.capacity)
    }

    var isFull: Bool { count == capacity }

    mutating func append(_ element: Element) {
        storage[writeIndex] = element
        writeIndex = (writeIndex + 1) % capacity
        count = min(count + 1, capacity)
    }

    mutating func clear() {
        storage = Array(repeating: nil, count: capacity)
        count = 0
        writeIndex = 0
    }

    mutating func resize(capacity newCapacity: Int) {
        let clamped = max(newCapacity, 1)
        guard clamped != capacity else { return }

        let preserved = snapshot()
        capacity = clamped
        storage = Array(repeating: nil, count: capacity)
        count = 0
        writeIndex = 0

        for element in preserved.suffix(capacity) {
            append(element)
        }
    }

    func snapshot() -> [Element] {
        guard count > 0 else { return [] }
        let start = count == capacity ? writeIndex : 0
        return (0..<count).compactMap { offset in
            storage[(start + offset) % capacity]
        }
    }
}
