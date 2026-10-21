import AppKit

@MainActor
final class CharacterView: NSView {
    let session: CharacterSession
    let finished: () -> Void
    let reportError: (Error) -> Void
    private let content = NSStackView()
    private var nameField: NSTextField?
    private var selectedAttribute = 0
    init(session: CharacterSession, finished: @escaping () -> Void, reportError: @escaping (Error) -> Void) {
        self.session = session; self.finished = finished; self.reportError = reportError
        super.init(frame: .zero)
        wantsLayer = true; layer?.backgroundColor = NSColor.windowBackgroundColor.cgColor
        content.orientation = .vertical; content.alignment = .leading; content.spacing = 12
        content.translatesAutoresizingMaskIntoConstraints = false
        addSubview(content)
        NSLayoutConstraint.activate([
            content.centerXAnchor.constraint(equalTo: centerXAnchor), content.centerYAnchor.constraint(equalTo: centerYAnchor),
            content.widthAnchor.constraint(equalTo: widthAnchor, multiplier: 0.83)])
        refresh()
    }
    required init?(coder: NSCoder) { fatalError() }
    override var acceptsFirstResponder: Bool { true }
    private func text(_ title: String, size: CGFloat = 14) {
        let label = NSTextField(wrappingLabelWithString: title)
        label.font = .systemFont(ofSize: size, weight: size > 20 ? .semibold : .regular)
        content.addArrangedSubview(label)
    }
    private func button(_ title: String, tag: Int, action: Selector) -> NSButton {
        let b = NSButton(title: title, target: self, action: action); b.tag = tag; return b
    }
    func refresh() {
        for view in content.arrangedSubviews { content.removeArrangedSubview(view); view.removeFromSuperview() }
        nameField = nil
        text("Character Generation", size: 28)
        text("ULTIMA I · The First Age of Darkness", size: 12)
        do {
            let values = try session.values()
            if session.stage == .attributes {
                text("능력치 배분 · 남은 점수 \(session.remaining)", size: 18)
                for i in 0..<6 {
                    let label = NSTextField(labelWithString: "\(i == selectedAttribute ? "▸" : " ") \(CharacterSession.attributes[i])")
                    label.widthAnchor.constraint(equalToConstant: 155).isActive = true
                    let value = NSTextField(labelWithString: "\(values[i])")
                    value.font = .monospacedDigitSystemFont(ofSize: 17, weight: .medium)
                    value.widthAnchor.constraint(equalToConstant: 35).isActive = true
                    let minus = button("−", tag: i*2, action: #selector(adjust(_:)))
                    minus.isEnabled = values[i] > 10
                    let plus = button("+", tag: i*2+1, action: #selector(adjust(_:)))
                    plus.isEnabled = values[i] < 25 && session.remaining > 0
                    content.addArrangedSubview(NSStackView(views: [label, minus, value, plus]))
                }
                text("각 능력치 10–25 · 방향키로 선택·조절 · 모두 배분한 뒤 Space")
            } else {
                text(zip(CharacterSession.attributes, values).map { "\($0.0) \($0.1)" }.joined(separator: "   "), size: 13)
                switch session.stage {
                case .race:
                    text("Select thy race", size: 20)
                    choices(CharacterSession.races, selected: session.race)
                    text("Human: Intelligence +5 · Elf: Agility +5\nDwarf: Strength +5 · Bobbit: Wisdom +10, Strength −5")
                case .sex:
                    text("Select thy sex", size: 20); choices(["Male", "Female"], selected: session.sex)
                case .profession:
                    text("Select thy class", size: 20); choices(CharacterSession.classes, selected: session.profession)
                    text("Fighter: Strength / Agility +10 · Cleric: Wisdom +10\nWizard: Intelligence +10 · Thief: Agility +10")
                case .name:
                    text("Enter thy name", size: 20)
                    let field = NSTextField(string: session.name)
                    field.placeholderString = "이름 (영문으로 시작, 최대 13자)"
                    field.target = self; field.action = #selector(nextStage)
                    field.widthAnchor.constraint(equalToConstant: 300).isActive = true
                    content.addArrangedSubview(field); nameField = field
                    text("원본과 같이 영문·숫자·기호를 사용합니다. 단어 첫 글자 외 대문자는 소문자로 바뀝니다.")
                case .confirmation, .saved:
                    text(session.name, size: 24)
                    text("\(CharacterSession.races[session.race]) · \(["Male", "Female"][session.sex]) · \(CharacterSession.classes[session.profession])")
                    text(session.stage == .saved ? "인물이 저장되었습니다. 다음 구현 단계는 소사리아로 진입하는 화면입니다." : "Save this character? (Y–N)")
                default: break
                }
            }
            let row = NSStackView(); row.spacing = 10
            row.addArrangedSubview(button("타이틀", tag: 0, action: #selector(exitToTitle)))
            if session.stage != .attributes && session.stage != .saved {
                row.addArrangedSubview(button("이전", tag: 0, action: #selector(previous)))
            }
            if session.stage != .saved {
                let next = button(session.stage == .confirmation ? "인물 저장" : "계속", tag: 0, action: #selector(nextStage))
                next.isEnabled = session.stage != .attributes || session.remaining == 0
                row.addArrangedSubview(next)
            } else {
                row.addArrangedSubview(button("새 인물 만들기", tag: 0, action: #selector(newCharacter)))
            }
            content.addArrangedSubview(row)
            if let nameField { window?.makeFirstResponder(nameField) }
        } catch { reportError(error) }
    }
    private func choices(_ labels: [String], selected: Int) {
        for (i,label) in labels.enumerated() {
            let b = NSButton(radioButtonWithTitle: "\(Character(UnicodeScalar(65+i)!))) \(label)", target: self, action: #selector(selectChoice(_:)))
            b.tag = i; b.state = i == selected ? .on : .off
            content.addArrangedSubview(b)
        }
    }
    @objc private func selectChoice(_ sender: NSButton) {
        switch session.stage {
        case .race: session.race = sender.tag
        case .sex: session.sex = sender.tag
        case .profession: session.profession = sender.tag
        default: return
        }
        refresh()
    }
    @objc private func adjust(_ sender: NSButton) {
        selectedAttribute = sender.tag/2
        _ = session.adjust(selectedAttribute, by: sender.tag % 2 == 0 ? -1 : 1); refresh()
        window?.makeFirstResponder(self)
    }
    @objc private func previous() {
        if let field = nameField { session.name = CharacterSession.normalizeName(field.stringValue) }
        session.stage = CharacterSession.Stage(rawValue: session.stage.rawValue-1) ?? .attributes
        refresh(); window?.makeFirstResponder(nameField ?? self)
    }
    @objc private func nextStage() {
        do {
            if session.stage == .attributes && session.remaining != 0 { NSSound.beep(); return }
            if let field = nameField {
                session.name = CharacterSession.normalizeName(field.stringValue)
                guard !session.name.isEmpty else { NSSound.beep(); return }
            }
            if session.stage == .confirmation {
                let directory = try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
                    appropriateFor: nil, create: true).appendingPathComponent("UltimaI/Characters/\(UUID().uuidString)")
                try session.save(to: directory)
            } else {
                session.stage = CharacterSession.Stage(rawValue: session.stage.rawValue+1) ?? .saved
            }
            refresh(); window?.makeFirstResponder(nameField ?? self)
        } catch { reportError(error) }
    }
    @objc private func newCharacter() {
        session.allocation = Array(repeating: 10, count: 6)
        session.race = 0; session.sex = 0; session.profession = 0; session.name = ""
        session.stage = .attributes; refresh()
    }
    @objc private func exitToTitle() { finished() }
    override func keyDown(with event: NSEvent) {
        if event.keyCode == 53 { exitToTitle(); return }
        if session.stage == .attributes {
            switch event.keyCode {
            case 123: _ = session.adjust(selectedAttribute, by: -1)
            case 124: _ = session.adjust(selectedAttribute, by: 1)
            case 125: selectedAttribute = (selectedAttribute+1)%6
            case 126: selectedAttribute = (selectedAttribute+5)%6
            case 49: nextStage(); return
            default: super.keyDown(with: event); return
            }
            refresh(); return
        }
        if event.keyCode == 36 { nextStage(); return }
        if let c = event.charactersIgnoringModifiers?.uppercased().utf8.first,
           (65...68).contains(c), [.race, .sex, .profession].contains(session.stage) {
            let i = Int(c-65)
            if session.stage == .sex && i > 1 { return }
            switch session.stage {
            case .race: session.race = i
            case .sex: session.sex = i
            default: session.profession = i
            }
            nextStage(); return
        }
        if session.stage == .confirmation, event.charactersIgnoringModifiers?.lowercased() == "y" { nextStage(); return }
        if session.stage == .confirmation, event.charactersIgnoringModifiers?.lowercased() == "n" { newCharacter(); return }
        super.keyDown(with: event)
    }
}
