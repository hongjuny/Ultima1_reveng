; Actor type and first hit/miss roll at $8D08-$8D2A.
.setcpu "6502"
.segment "CODE"

hit_roll:
        sec
        sbc     #$30
        sta     $72
        cmp     #$00
        bne     chance
        lda     #$01
        sta     $9E2A
chance:
        ldx     $72
        lda     #$80
        clc
        adc     $7ECA
        sta     $73
        jsr     $15B9
        cmp     $73
        .byte   $B0, $D0       ; BCS $8CF7 (miss)
        lda     #$01
        sta     $9E2A
