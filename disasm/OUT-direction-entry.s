; Outdoor direction dispatch at $9351-$936C. The four table entries
; choose a one-unit change to zero-page $00/$01, then share $936D.
.setcpu "6502"
.segment "CODE"

direction_prepare:
        ldx     $00
        ldy     $01
        clc
        rts

key_0b:
        jsr     direction_prepare
        dey
        bcc     common
key_0a:
        jsr     direction_prepare
        iny
        bcc     common
key_15:
        jsr     direction_prepare
        inx
        bcc     common
key_08:
        jsr     direction_prepare
        dex
common:
