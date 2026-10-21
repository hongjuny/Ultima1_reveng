; Shared input paths at $1D7E-$1DD5. The first RTS overlaps the end
; of STUPH-keyboard-latch.s and is the early return from the poll loop.
; $15C2 -> $1D97: bounded poll. $15C5 -> $1DA3: scene update before poll.
; Both paths consume the first buffered key and restore X/Y at $1DCD.
.setcpu "6502"
.segment "CODE"

poll_return:
        rts
poll_seven:
        ldy     #$07
poll_again:
        jsr     $1D64
        lda     $78
        bne     poll_return
        lda     #$4F
        jsr     $160B
        dey
        bne     poll_again
        rts

wait_for_key:
        jsr     bounded_input
        beq     wait_for_key
        rts

bounded_input:
        jsr     $1DD6
        jsr     poll_seven
        lda     $78
        bne     consume_key
        beq     finish_input

outdoor_input:
        jsr     $1DD6
        jsr     $1C39
        lda     $78
        beq     finish_input

consume_key:
        lda     #$20
        jsr     $1A1D
        lda     $74
        dec     $78
        ldx     #$01
        cmp     #$FF
        bne     normalize_key
        lda     #$88
normalize_key:
        cmp     #$E0
        bcc     shift_buffer
        eor     #$20
shift_buffer:
        ldy     $74,x
        sty     $73,x
        inx
        cpx     #$04
        bcc     shift_buffer
finish_input:
        ldx     $1764
        ldy     $1765
        and     #$7F
        rts
