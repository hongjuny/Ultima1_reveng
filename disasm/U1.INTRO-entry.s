; Two entry vectors at $0800-$0805.
.setcpu "6502"
.segment "CODE"

first_entry:
        jmp     $0F23
second_entry:
        jmp     $0F41
