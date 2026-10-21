; Monster hit threshold and comparison at $9A37-$9A63.
; threshold = ($7ECC >> 1) + 8*$7E7B + $38 (8-bit wrap).
.setcpu "6502"
.segment "CODE"

hit_roll:
        lda     $7ECC
        lsr     a
        clc
        adc     $7E7B
        adc     $7E7B
        adc     $7E7B
        adc     $7E7B
        adc     $7E7B
        adc     $7E7B
        adc     $7E7B
        adc     $7E7B
        adc     #$38
        sta     $A4F2
        sta     $A4FC
        jsr     $15B9
        cmp     $A4F2
        .byte   $B0, $0E       ; BCS $9A72 (hit path)
