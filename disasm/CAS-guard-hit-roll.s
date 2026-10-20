; Castle guard retaliation hit threshold at $9951-$9980.
.setcpu "6502"
.segment "CODE"

guard_hit_roll:
        lda     #$04
        jsr     $15CB
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
        sta     $72
        sta     $9E29
        jsr     $15B9
        cmp     $72
        .byte   $B0, $0E       ; BCS $998F (guard hit)
