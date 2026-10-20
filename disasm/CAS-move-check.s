; Castle movement candidate and collision decision at $8C00-$8C12.
.setcpu "6502"
.segment "CODE"

propose:
        txa
        clc
        adc     $00
        sta     $0C
        tax
        tya
        clc
        adc     $01
        sta     $0D
        tay
        jsr     $9BC0
        .byte   $B0, $16       ; BCS $8C29: passable/available
