; Castle hit damage roll and actor HP subtraction at $8D46-$8D83.
.setcpu "6502"
.segment "CODE"

roll_damage:
        lda     $7EC8
        clc
        adc     $7E7A
        adc     $7E7A
        adc     $7E7A
        sta     $73
retry:
        jsr     $15B9
        cmp     #$00
        beq     retry
        cmp     $73
        bcs     retry
        sta     $73
        lda     #$02
        jsr     $15CB
        ldx     $9E36
        bne     subtract_hp
        lda     $7EED
        beq     no_subtract
subtract_hp:
        lda     $B6DC,x
        sec
        sbc     $73
        sta     $B6DC,x
        lda     $B6EC,x
        sbc     #$00
        sta     $B6EC,x
        .byte   $90, $16       ; BCC $8D9A (actor killed)
no_subtract:
