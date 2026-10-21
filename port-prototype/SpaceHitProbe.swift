@main
struct SpaceHitProbe {
    static func main() {
        precondition(CommandLine.arguments.count == 5,
                     "usage: SpaceHitProbe ship-byte experience ace-count Y")
        let inputs = CommandLine.arguments.dropFirst().map { Int($0)! }
        precondition((0...255).contains(inputs[0]) &&
                     (0...65535).contains(inputs[1]) &&
                     (0...255).contains(inputs[2]) &&
                     (0...255).contains(inputs[3]))
        var memory = [UInt8](repeating: 0, count: 65536)
        let y = UInt8(inputs[3])
        memory[0xB099 + Int(y)] = UInt8(inputs[0])
        memory[0x7EE7] = UInt8(truncatingIfNeeded: inputs[1])
        memory[0x7EE8] = UInt8(truncatingIfNeeded: inputs[1] >> 8)
        memory[0x7EB6] = UInt8(inputs[2])
        let exit = SpaceHitPort.apply(memory: &memory, y: y)
        let experience = Int(memory[0x7EE7]) + 256 * Int(memory[0x7EE8])
        let fields = [String(memory[0xB099 + Int(y)]), String(experience),
                      String(memory[0x7EB6]), exit.branch.rawValue,
                      String(exit.accumulator), exit.carry ? "1" : "0",
                      exit.zero ? "1" : "0", exit.negative ? "1" : "0"]
        print(fields.joined(separator: " "))
    }
}
