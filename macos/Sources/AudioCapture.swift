import Foundation
import AVFoundation

// Execute original effects independently, without opening an audio device.
func captureAudio(resources: URL, output: URL) throws {
    try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
    var report = [String: Any]()
    for (name, entry, expectedCount, gap) in [("0E",0x1B32,16,6441),("10",0x1B42,50,1666)] {
        let cpu = try StartupMachine(resources: resources)
        try cpu.load("STUPH", at: 0x0800)
        cpu.gameRunning = true; cpu.engineLoaded = true
        cpu.pc = entry; cpu.speaker.enabled = true; cpu.speaker.reset()
        for _ in 0..<1_000_000 {
            if cpu.pc == 0x1B41 { break }
            _ = try cpu.nextGameFrame(budget: 1)
        }
        let edges = cpu.speaker.edges
        guard edges.count == expectedCount,
              zip(edges, edges.dropFirst()).allSatisfy({ $1 - $0 == gap }) else {
            throw StartupFailure.unsupported("Original sound \(name) edge timing differs: \(edges)")
        }
        let samples = cpu.speaker.drain()
        guard samples.contains(where: { abs($0) > 0.01 }), samples.allSatisfy({ $0.isFinite && abs($0) < 0.5 }) else {
            throw StartupFailure.unsupported("Invalid speaker waveform")
        }
        let format = AVAudioFormat(standardFormatWithSampleRate: AppleSpeaker.rate, channels: 1)!
        let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(samples.count))!
        buffer.frameLength = buffer.frameCapacity
        samples.withUnsafeBufferPointer { buffer.floatChannelData![0].update(from: $0.baseAddress!, count: samples.count) }
        let file = try AVAudioFile(forWriting: output.appendingPathComponent(name + ".wav"), settings: format.settings)
        try file.write(from: buffer)
        report[name] = ["edges": edges.count,"gap_cycles": gap,"samples": samples.count,"rate": AppleSpeaker.rate]
        print("Original effect \(name): \(edges.count) edges, \(gap)-cycle gaps, \(samples.count) PCM samples")
    }
    // Exercise the actual original nine-way stack dispatcher and effect returns.
    var effects = [[String: Int]]()
    for id in stride(from: 0, through: 16, by: 2) {
        let cpu = try StartupMachine(resources: resources)
        try cpu.load("STUPH", at: 0x0800)
        cpu.gameRunning = true; cpu.engineLoaded = true
        cpu.memory[0x1580] = 0; cpu.memory[0x1581] = 1
        cpu.a = UInt8(id); cpu.pc = 0x1AC4; cpu.pushWord(0x1233)
        cpu.speaker.enabled = true; cpu.speaker.reset()
        for _ in 0..<2_000_000 {
            if cpu.pc == 0x1234 { break }
            _ = try cpu.nextGameFrame(budget: 1)
        }
        guard cpu.pc == 0x1234 && !cpu.speaker.edges.isEmpty else {
            throw StartupFailure.unsupported("Sound dispatcher did not return for ID \(id)")
        }
        let count = cpu.speaker.edges.count
        let pcm = cpu.speaker.drain()
        guard pcm.contains(where: { abs($0) > 0.01 }), pcm.allSatisfy({ $0.isFinite && abs($0) < 0.5 }) else {
            throw StartupFailure.unsupported("Sound dispatcher waveform invalid for ID \(id)")
        }
        effects.append(["id": id,"edges": count,"samples": pcm.count])
    }
    report["dispatcher"] = effects
    print("All nine original sound effects dispatched, rendered and returned")
    // Write accesses must toggle the same latch as reads.
    let cpu = try StartupMachine(resources: resources)
    cpu.speaker.enabled = true
    cpu.write(0xC030, 0); _ = cpu.read(0xC030)
    guard cpu.speaker.edges.count == 2 else { throw StartupFailure.unsupported("Speaker write/read mismatch") }
    try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted,.sortedKeys]).write(to: output.appendingPathComponent("audio.json"))
}
