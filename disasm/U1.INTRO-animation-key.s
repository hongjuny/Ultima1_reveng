; Keyboard poll during the intro animation, $0B23-$0B4F.
.setcpu "6502"
.segment "CODE"

animation_key_poll:
        lda     $C000
        .byte   $10, $38       ; BPL $0B60, RTS outside this fragment
        bit     $C010
        bit     $C030
        ldx     #$00
speaker_delay:
        dex
        bne     speaker_delay
        bit     $C030
        cmp     #$CB
        beq     special_k
        cmp     #$80
        .byte   $D0, $12       ; BNE $0B50, MI.U1 request outside fragment
        lda     #$10
        sta     $03CE
        bit     $C030
        rts
special_k:
        lda     #$04
        sta     $03CE
        bit     $C030
        rts
