import AppKit
import ImageIO

enum HGRRenderer {
    static let width = 560, height = 192
    static let palette: [UInt32] = [
        0x000000, 0x000000, 0xC734FF, 0xFFFFFF,
        0x000000, 0x38CB00, 0xFFFFFF, 0xFFFFFF,
        0x000000, 0x000000, 0x0DA1FF, 0xFFFFFF,
        0x000000, 0xF25E00, 0xFFFFFF, 0xFFFFFF
    ]

    static func pixels(memory: [UInt8], page: Int) -> Data {
        var pixels = [UInt8](repeating: 255, count: width * height * 4)
        for row in 0..<height {
            let offset = ((row & 7) << 10) | (((row >> 3) & 7) << 7) | ((row >> 6) * 40)
            for column in 0..<40 {
                let address = page + offset + column
                let previous = column > 0 ? memory[address - 1] : 0
                let current = memory[address]
                let following = column < 39 ? memory[address + 1] : 0
                var stream = (Int(following & 1) << 8) | (Int(current & 0x7F) << 1) | Int(previous >> 6 & 1)
                let phase = Int(current >> 7) * 8
                for bit in 0..<7 {
                    var window = stream & 7
                    if (column + bit) & 1 != 0 && (window == 2 || window == 5) { window ^= 7 }
                    let color = palette[window + phase]
                    for doubled in 0..<2 {
                        let index = (row * width + column * 14 + bit * 2 + doubled) * 4
                        pixels[index] = UInt8(truncatingIfNeeded: color >> 16)
                        pixels[index + 1] = UInt8(truncatingIfNeeded: color >> 8)
                        pixels[index + 2] = UInt8(truncatingIfNeeded: color)
                    }
                    stream >>= 1
                }
            }
        }
        return Data(pixels)
    }

    static func image(memory: [UInt8], page: Int) -> CGImage {
        let data = pixels(memory: memory, page: page)
        let provider = CGDataProvider(data: data as CFData)!
        return CGImage(width: width, height: height, bitsPerComponent: 8,
                       bitsPerPixel: 32, bytesPerRow: width * 4,
                       space: CGColorSpaceCreateDeviceRGB(),
                       bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.last.rawValue),
                       provider: provider, decode: nil, shouldInterpolate: false,
                       intent: .defaultIntent)!
    }

    static func save(_ image: CGImage, to url: URL) throws {
        guard let destination = CGImageDestinationCreateWithURL(url as CFURL, "public.png" as CFString, 1, nil) else {
            throw StartupFailure.unsupported("Cannot create PNG at \(url.path)")
        }
        CGImageDestinationAddImage(destination, image, nil)
        guard CGImageDestinationFinalize(destination) else {
            throw StartupFailure.unsupported("Cannot save PNG at \(url.path)")
        }
    }
}
