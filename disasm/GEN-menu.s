; Character menu choice at $89FD-$8A0F.
.setcpu "6502"
.segment "CODE"

read_choice:
        jsr     $15BF
        pha
        jsr     $93CC
        pla
        cmp     #$41
        bne     check_continue
        jmp     $8AC3
check_continue:
        cmp     #$42
        bne     read_choice
