; OUT post-load HP gate at $898A-$8994.
.setcpu "6502"
.segment "CODE"

health_gate:
        jsr     $94C1
        lda     $7EC6
        ora     $7EC7
        .byte   $F0, $53       ; BEQ $89E8: resurrection path
