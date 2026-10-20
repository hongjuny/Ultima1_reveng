; E command gate at $90C8-$90DC. It saves current coordinates,
; reads the decoded tile, and accepts codes $04-$07.
.setcpu "6502"
.segment "CODE"

enter_gate:
        ldx     $00
        ldy     $01
        stx     $7E73
        sty     $7E74
        jsr     $99F8
        cmp     #$04
        .byte   $90, $EC       ; BCC $90C5
        cmp     #$08
        .byte   $B0, $E8       ; BCS $90C5
