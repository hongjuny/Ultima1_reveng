import Foundation
import AVFoundation

// An independent audio clock: it never throttles or changes game execution.
// $C030 is a one-bit latch, not a sound-effect lookup or sampled replacement.
final class AppleSpeaker {
    static let rate = 48_000.0
    static let cpuRate = 1_023_000.0
    var enabled = false
    private(set) var cycles = 0
    private(set) var edges: [Int] = []
    private var level: Float = -0.18
    private var renderedCycle = 0.0
    private var previousInput: Float = 0
    private var previousOutput: Float = 0

    // NMOS 6502 base cycles. Runtime branch and indexed-read penalties below.
    private static let base: [Int] = [
        7,6,2,8,3,3,5,5,3,2,2,2,4,4,6,6,
        2,5,2,8,4,4,6,6,2,4,2,7,4,4,7,7,
        6,6,2,8,3,3,5,5,4,2,2,2,4,4,6,6,
        2,5,2,8,4,4,6,6,2,4,2,7,4,4,7,7,
        6,6,2,8,3,3,5,5,3,2,2,2,3,4,6,6,
        2,5,2,8,4,4,6,6,2,4,2,7,4,4,7,7,
        6,6,2,8,3,3,5,5,4,2,2,2,5,4,6,6,
        2,5,2,8,4,4,6,6,2,4,2,7,4,4,7,7,
        2,6,2,6,3,3,3,3,2,2,2,2,4,4,4,4,
        2,6,2,6,4,4,4,4,2,5,2,5,5,5,5,5,
        2,6,2,6,3,3,3,3,2,2,2,2,4,4,4,4,
        2,5,2,5,4,4,4,4,2,4,2,4,4,4,4,4,
        2,6,2,8,3,3,5,5,2,2,2,2,4,4,6,6,
        2,5,2,8,4,4,6,6,2,4,2,7,4,4,7,7,
        2,6,2,8,3,3,5,5,2,2,2,2,4,4,6,6,
        2,5,2,8,4,4,6,6,2,4,2,7,4,4,7,7]

    @inline(__always) func clockInstruction(_ cpu: StartupMachine) {
        guard enabled else { return }
        let op = Int(cpu.memory[cpu.pc])
        var count = Self.base[op]
        if op & 0x1F == 0x10 {
            let masks: [UInt8] = [0x80,0x40,1,2]
            let taken = cpu.flag(masks[op >> 6]) == (op & 0x20 != 0)
            if taken {
                let next = (cpu.pc + 2) & 0xFFFF
                let target = (next + Int(Int8(bitPattern: cpu.byteOperand()))) & 0xFFFF
                count += 1 + (next & 0xFF00 == target & 0xFF00 ? 0 : 1)
            }
        } else if [0x11,0x31,0x51,0x71,0xB1,0xD1,0xF1].contains(op) {
            let address = cpu.zpWord(cpu.byteOperand())
            if (address & 255) + Int(cpu.y) > 255 { count += 1 }
        } else if [0x19,0x39,0x59,0x79,0xB9,0xD9,0xF9,0x1D,0x3D,0x5D,0x7D,0xBC,0xBD,0xBE,0xDD,0xFD].contains(op) {
            let index = op & 15 == 9 || op == 0xBE ? cpu.y : cpu.x
            if (cpu.wordOperand() & 255) + Int(index) > 255 { count += 1 }
        }
        cycles += count
    }
    func toggle() { if enabled { edges.append(cycles) } }

    // Integrate each sample interval, including multiple edges, to limit aliasing.
    // A DC blocker makes the latched constant voltage decay to silence.
    func drain() -> [Float] {
        guard enabled else { edges.removeAll(keepingCapacity: true); return [] }
        let width = Self.cpuRate / Self.rate
        let count = max(0, Int((Double(cycles) - renderedCycle) / width))
        var result = [Float](); result.reserveCapacity(count)
        var edge = 0
        for _ in 0..<count {
            let end = renderedCycle + width
            var cursor = renderedCycle, integral = 0.0
            while edge < edges.count && Double(edges[edge]) <= end {
                let time = max(cursor, Double(edges[edge]))
                integral += (time - cursor) * Double(level)
                cursor = time; level = -level; edge += 1
            }
            integral += (end - cursor) * Double(level)
            let input = Float(integral / width)
            let output = input - previousInput + 0.995 * previousOutput
            previousInput = input; previousOutput = output
            result.append(output); renderedCycle = end
        }
        edges.removeFirst(edge)
        return result
    }
    func reset() {
        cycles = 0; renderedCycle = 0; edges.removeAll(keepingCapacity: true)
        level = -0.18; previousInput = level; previousOutput = 0
    }
}

// All scheduling is on the main thread. AVAudioPlayerNode owns queued PCM buffers.
final class SpeakerOutput {
    private let engine = AVAudioEngine()
    private let player = AVAudioPlayerNode()
    private let format = AVAudioFormat(standardFormatWithSampleRate: AppleSpeaker.rate, channels: 1)!
    private var queuedUntil = Date.distantPast
    private var started = false
    func submit(_ samples: [Float]) throws {
        guard !samples.isEmpty else { return }
        // Don't queue silent game polling; it would put effects behind idle time.
        guard let first = samples.firstIndex(where: { abs($0) > 0.0001 }),
              let last = samples.lastIndex(where: { abs($0) > 0.0001 }) else { return }
        let audible = samples[first...last]
        if !started {
            engine.attach(player); engine.connect(player, to: engine.mainMixerNode, format: format)
            try engine.start(); player.play(); started = true
        }
        if !engine.isRunning { try engine.start() }
        let now = Date()
        if queuedUntil.timeIntervalSince(now) > 0.25 { flush() }
        let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(audible.count))!
        buffer.frameLength = buffer.frameCapacity
        audible.withUnsafeBufferPointer { buffer.floatChannelData![0].update(from: $0.baseAddress!, count: audible.count) }
        player.scheduleBuffer(buffer)
        if !player.isPlaying { player.play() }
        queuedUntil = max(now, queuedUntil).addingTimeInterval(Double(audible.count) / AppleSpeaker.rate)
    }
    func flush() { player.stop(); queuedUntil = .distantPast }
}
