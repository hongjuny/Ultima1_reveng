; $1B32-$1B47: two sound IDs share a $C030 toggle loop.
; ID $0E enters at $1B32 (16 toggles); ID $10 enters at $1B42
; (50 toggles). $1608 controls the interval and is not classified here.
.setcpu "6502"
.segment "CODE"

effect_0e:
        ldy     #$10
        lda     #$30
toggle_loop:
        pha
        jsr     $1608
        bit     $C030
        pla
        dey
        bne     toggle_loop
        rts

effect_10:
        ldy     #$32
        lda     #$17
        bne     toggle_loop
