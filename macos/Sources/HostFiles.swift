import Foundation

extension StartupMachine {
    var playerDirectory: URL {
        saveDirectory ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("UltimaI/Characters")
    }
    func word(at address: Int) -> Int { Int(memory[address]) | Int(memory[address+1]) << 8 }
    func filename(at address: Int) -> String {
        var bytes = [UInt8]()
        for offset in 0..<128 {
            let c = memory[(address+offset)&0xFFFF] & 0x7F
            if c == 0 { break }
            bytes.append(c)
        }
        return String(bytes: bytes, encoding: .ascii) ?? ""
    }
    func setFilename(_ path: String) {
        let bytes = Array(path.utf8)
        memory[0xBA79] = UInt8(bytes.count)
        for (i,c) in bytes.enumerated() { memory[0xBA7A+i] = c }
    }
    // ProDOS wrapper ABI: B736 filename pointer; B71E aux-address load;
    // B721 explicit destination + filename pointer. Original callers remain intact.
    func hostFileService() throws {
        let service = pc
        let args = popWord()+1
        let resume = args + (service == 0xB721 ? 4 : 2)
        if service == 0xB736 {
            setFilename(filename(at: word(at: args)))
            a = nz(0); setFlag(1, false); pc = resume; return
        }
        let pointer = word(at: args + (service == 0xB721 ? 2 : 0))
        let path = filename(at: pointer)
        setFilename(path)
        let name = path.split(separator: "/").last.map(String.init) ?? path
        let destination: Int
        let data: Data
        if name == "U1.VARS" {
            destination = service == 0xB721 ? word(at: args) : 0x7E6D
            let file = playerDirectory.appendingPathComponent(name)
            guard FileManager.default.fileExists(atPath: file.path) else {
                // The original GEN read-error path asks for removable media.
                // This port uses a local record: retain its renderer and retry
                // flow, but explain the actionable cause in the same text slot.
                if overlay == "GEN" {
                    let address = 0x8A36
                    let original = Array("Please put in the Player disk.".utf8)
                    let replacement = Array("No saved game. Create with A. ".utf8)
                    if Array(memory[address..<address+original.count]) == original {
                        memory.replaceSubrange(address..<address+original.count, with: replacement)
                    }
                }
                a = nz(6); setFlag(1, true); pc = resume; return
            }
            data = try Data(contentsOf: file)
            guard data.count == 458 else { throw StartupFailure.unsupported("Invalid U1.VARS length") }
        } else {
            guard !path.hasPrefix("/RAM/") else {
                a = nz(7); setFlag(1, true); pc = resume; return
            }
            guard ["OUT", "TWN", "CAS", "DNG", "SPA", "TCMAPS", "MAPCHARS"].contains(name) else { throw StartupFailure.unsupported("Module not yet translated: \(name)") }
            destination = service == 0xB721 ? word(at: args) : 0x8956
            data = try Data(contentsOf: resources.appendingPathComponent(name))
            if ["OUT", "TWN", "CAS", "DNG", "SPA"].contains(name) { overlay = name }
        }
        guard destination+data.count <= 65536 else { throw StartupFailure.unsupported("File exceeds RAM") }
        memory.replaceSubrange(destination..<destination+data.count, with: data)
        memory[0xBAF2] = UInt8(truncatingIfNeeded: destination)
        memory[0xBAF3] = UInt8(truncatingIfNeeded: destination >> 8)
        memory[0xBAF6] = UInt8(truncatingIfNeeded: data.count)
        memory[0xBAF7] = UInt8(truncatingIfNeeded: data.count >> 8)
        a = nz(0); setFlag(1, false); pc = resume
    }
}
