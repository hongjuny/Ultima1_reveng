; Outdoor 64x64 tile lookup at $99D1-$99F7. Raw tile byte at
; $6000 + y*64 + x is shifted right before returning.
.setcpu "6502"
.segment "CODE"

tile_at_xy:
        lda     #$00
        cpy     #$40
        bcs     out_of_range
        cpx     #$40
        bcs     out_of_range
        tya
        sta     restore_y + 1
        lsr     a
        sta     $73
        lda     #$00
        ror     a
        lsr     $73
        ror     a
        sta     $72
        lda     $73
        adc     #$60
        sta     $73
        txa
        tay
        lda     ($72),y
restore_y:
        ldy     #$00
out_of_range:
        lsr     a
        rts
