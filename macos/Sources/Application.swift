import AppKit

@MainActor
final class GameView: NSView {
    var begin: (() -> Void)?
    override var acceptsFirstResponder: Bool { true }
    override func keyDown(with event: NSEvent) {
        if event.keyCode == 36 || event.keyCode == 49 { begin?() } else { super.keyDown(with: event) }
    }
    var frameImage: CGImage? { didSet { needsDisplay = true } }
    override var isOpaque: Bool { true }
    override func draw(_ dirtyRect: NSRect) {
        NSColor.black.setFill(); bounds.fill()
        guard let frameImage, let context = NSGraphicsContext.current?.cgContext else { return }
        let size = min(bounds.width / 4, bounds.height / 3)
        let rect = CGRect(x: (bounds.width - size * 4) / 2,
                          y: (bounds.height - size * 3) / 2,
                          width: size * 4, height: size * 3)
        context.interpolationQuality = .none
        context.draw(frameImage, in: rect)
    }
}

@MainActor
final class ApplicationDelegate: NSObject, NSApplicationDelegate, NSToolbarDelegate {
    let resources: URL
    var window: NSWindow!
    let screen = GameView()
    var machine: StartupMachine!
    var timer: Timer?
    var resumeAt = Date.distantPast
    var paused = false

    init(resources: URL) { self.resources = resources }

    func applicationDidFinishLaunching(_ notification: Notification) {
        let app = NSApplication.shared
        app.setActivationPolicy(.regular)
        let menu = NSMenu()
        let applicationItem = NSMenuItem(); menu.addItem(applicationItem)
        let applicationMenu = NSMenu(); applicationItem.submenu = applicationMenu
        applicationMenu.addItem(withTitle: "Ultima I 종료", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        let playbackItem = NSMenuItem(); menu.addItem(playbackItem)
        let playback = NSMenu(title: "재생"); playbackItem.submenu = playback
        playback.addItem(withTitle: "처음부터 다시 보기", action: #selector(restart), keyEquivalent: "r").target = self
        let skipItem = playback.addItem(withTitle: "타이틀로 바로 이동", action: #selector(skipToTitle), keyEquivalent: "")
        skipItem.target = self; skipItem.keyEquivalentModifierMask = []
        let pauseItem = playback.addItem(withTitle: "일시 정지 / 계속", action: #selector(togglePause), keyEquivalent: "")
        pauseItem.target = self; pauseItem.keyEquivalentModifierMask = []
        playback.addItem(withTitle: "전체 화면", action: #selector(toggleFullscreen), keyEquivalent: "f").target = self
        app.mainMenu = menu

        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 800, height: 600),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable],
                          backing: .buffered, defer: false)
        window.title = "Ultima I"
        window.subtitle = "The First Age of Darkness"
        window.minSize = NSSize(width: 560, height: 440)
        window.contentView = screen
        screen.begin = { [weak self] in
            guard let self else { return }
            if self.machine?.titleReady == true { self.createCharacter() } else { self.skipToTitle() }
        }
        window.makeFirstResponder(screen)
        window.backgroundColor = .black
        window.collectionBehavior = [.fullScreenPrimary]
        let toolbar = NSToolbar(identifier: "Playback")
        toolbar.delegate = self
        toolbar.displayMode = .iconOnly
        window.toolbar = toolbar
        window.center(); window.makeKeyAndOrderFront(nil)
        app.activate(ignoringOtherApps: true)
        restart()
        if let index = CommandLine.arguments.firstIndex(of: "--window-capture"),
           index + 1 < CommandLine.arguments.count {
            skipToTitle()
            let path = CommandLine.arguments[index + 1]
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { [self] in
                screen.displayIfNeeded()
                if let bitmap = screen.bitmapImageRepForCachingDisplay(in: screen.bounds) {
                    screen.cacheDisplay(in: screen.bounds, to: bitmap)
                    try? bitmap.representation(using: .png, properties: [:])?.write(to: URL(fileURLWithPath: path))
                    print("Native window captured: \(path); visible=\(window.isVisible)")
                }
                NSApplication.shared.terminate(nil)
            }
            return
        }
        timer = Timer.scheduledTimer(withTimeInterval: 1.0 / 60.0, repeats: true) { [weak self] _ in
            MainActor.assumeIsolated { self?.advance() }
        }
    }

    @objc func restart() {
        do {
            window.contentView = screen
            window.makeFirstResponder(screen)
            machine = try StartupMachine(resources: resources)
            paused = false; resumeAt = .distantPast
        } catch { show(error) }
    }
    @objc func createCharacter() {
        do {
            let session = try CharacterSession(resources: resources)
            paused = true
            let view = CharacterView(session: session, finished: { [weak self] in
                guard let self else { return }
                self.window.contentView = self.screen
                self.window.makeFirstResponder(self.screen)
                self.skipToTitle()
            }, reportError: { [weak self] in self?.show($0) })
            window.contentView = view
            window.makeFirstResponder(view)
        } catch { show(error) }
    }
    @objc func togglePause() {
        guard machine?.titleReady != true else { return }
        paused.toggle()
    }
    @objc func skipToTitle() {
        guard let machine else { return }
        do {
            while !machine.titleReady && machine.instructions < 100_000_000 {
                _ = try machine.nextFrame()
            }
            screen.frameImage = HGRRenderer.image(memory: machine.memory, page: machine.page)
            paused = true
        } catch { paused = true; show(error) }
    }
    @objc func toggleFullscreen() { window.toggleFullScreen(nil) }
    func toolbarAllowedItemIdentifiers(_ toolbar: NSToolbar) -> [NSToolbarItem.Identifier] {
        toolbarDefaultItemIdentifiers(toolbar)
    }
    func toolbarDefaultItemIdentifiers(_ toolbar: NSToolbar) -> [NSToolbarItem.Identifier] {
        [.init("character"), .flexibleSpace, .init("pause"), .init("skip"), .init("replay"), .init("fullscreen")]
    }
    func toolbar(_ toolbar: NSToolbar, itemForItemIdentifier id: NSToolbarItem.Identifier,
                 willBeInsertedIntoToolbar flag: Bool) -> NSToolbarItem? {
        let definitions: [String: (String, String, Selector)] = [
            "character": ("새 인물 만들기", "person.crop.circle.badge.plus", #selector(createCharacter)),
            "pause": ("일시 정지 / 계속", "pause.fill", #selector(togglePause)),
            "skip": ("타이틀로 바로 이동", "forward.end.fill", #selector(skipToTitle)),
            "replay": ("처음부터 다시 보기", "arrow.counterclockwise", #selector(restart)),
            "fullscreen": ("전체 화면", "arrow.up.left.and.arrow.down.right", #selector(toggleFullscreen))]
        guard let (label, symbol, action) = definitions[id.rawValue] else { return nil }
        let item = NSToolbarItem(itemIdentifier: id)
        item.label = label; item.toolTip = label
        item.image = NSImage(systemSymbolName: symbol, accessibilityDescription: label)
        item.target = self; item.action = action
        return item
    }
    func advance() {
        guard let machine, !paused, Date() >= resumeAt else { return }
        do {
            let hadSplash = machine.splashPresented
            if try machine.nextFrame(budget: 150_000) {
                screen.frameImage = HGRRenderer.image(memory: machine.memory, page: machine.page)
                if !hadSplash && machine.splashPresented { resumeAt = Date().addingTimeInterval(1.4) }
                if machine.titleReady { paused = true }
            }
        } catch { paused = true; show(error) }
    }
    func show(_ error: Error) {
        let alert = NSAlert()
        alert.messageText = "Ultima I 작업을 완료할 수 없습니다"
        alert.informativeText = String(describing: error)
        alert.runModal()
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}

@main
struct UltimaStartupApplication {
    @MainActor static func main() {
        let arguments = CommandLine.arguments
        let resources: URL
        if let index = arguments.firstIndex(of: "--assets"), index + 1 < arguments.count {
            resources = URL(fileURLWithPath: arguments[index + 1])
        } else {
            resources = Bundle.main.resourceURL!.appendingPathComponent("OriginalData")
        }
        if let index = arguments.firstIndex(of: "--check-character"), index + 1 < arguments.count {
            do { try checkCharacterCreation(resources: resources, output: URL(fileURLWithPath: arguments[index+1])) }
            catch { fputs("Character checks failed: \(error)\n", stderr); exit(1) }
            return
        }
        if let index = arguments.firstIndex(of: "--capture"), index + 1 < arguments.count {
            do {
                let output = URL(fileURLWithPath: arguments[index + 1])
                try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
                let machine = try StartupMachine(resources: resources)
                var capture = 0
                var checkpoints = [[String: Any]]()
                for _ in 0..<1800 {
                    if try machine.nextFrame() {
                        if capture > 0 && capture % 60 == 0 {
                            try HGRRenderer.save(HGRRenderer.image(memory: machine.memory, page: machine.page),
                                                 to: output.appendingPathComponent(String(format: "intro-%04d.png", capture)))
                        }
                        if capture == 0 || capture == 1 || machine.titleReady {
                            let name = capture == 0 ? "origin" : capture == 1 ? "intro-first" : "title"
                            try HGRRenderer.save(HGRRenderer.image(memory: machine.memory, page: machine.page),
                                                 to: output.appendingPathComponent(name + ".png"))
                            try Data(machine.memory).write(to: output.appendingPathComponent(name + ".ram"))
                            try HGRRenderer.pixels(memory: machine.memory, page: machine.page)
                                .write(to: output.appendingPathComponent(name + ".rgba"))
                            checkpoints.append(["name": name, "pc": machine.pc, "page": machine.page,
                                                "a": Int(machine.a), "x": Int(machine.x), "y": Int(machine.y),
                                                "sp": Int(machine.sp), "p": Int(machine.p)])
                            print("\(name): PC=\(String(machine.pc, radix: 16)), page=\(String(machine.page, radix: 16)), \(machine.instructions) translated steps")
                        }
                        capture += 1
                        if machine.titleReady { break }
                    }
                    if machine.instructions > 100_000_000 {
                        throw StartupFailure.unsupported("Startup exceeded its instruction limit")
                    }
                }
                guard machine.titleReady else { throw StartupFailure.unsupported("Title checkpoint not reached") }
                let report: [String: Any] = ["frames": capture, "instructions": machine.instructions,
                    "visited_instructions": machine.visited.count, "title_pc": machine.pc,
                    "sound_edges": machine.soundEdges, "page": machine.page,
                    "hires": machine.hires, "text": machine.text, "checkpoints": checkpoints,
                    "title_phase": ["kind_09DD": Int(machine.memory[0x09DD]),
                                    "counter_09DC": Int(machine.memory[0x09DC]),
                                    "reveal_09DF": Int(machine.memory[0x09DF])]]
                try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
                    .write(to: output.appendingPathComponent("report.json"))
            } catch { fputs("Startup capture failed: \(error)\n", stderr); exit(1) }
            return
        }
        let app = NSApplication.shared
        let delegate = ApplicationDelegate(resources: resources)
        app.delegate = delegate
        withExtendedLifetime(delegate) { app.run() }
    }
}
