; $1B02-$1B31: sound queue push/pop using bytes $79-$7C and counter $7D.
.setcpu "6502"
.segment "CODE"

dequeue_sound:
        lda     $7D
        beq     dequeue_done
        lda     $79
        ldx     #$01
shift_queue:
        ldy     $79,x
        sty     $78,x
        inx
        cpx     #$04
        bcc     shift_queue
        jsr     $1AC4
        dec     $7D
dequeue_done:
        rts

enqueue_sound:
        ldx     $7D
        beq     store_sound
        ldy     $78,x
        bne     check_full
        dex
check_full:
        cpx     #$04
        bcc     store_sound
        pha
        jsr     dequeue_sound
        pla
        ldx     $7D
store_sound:
        sta     $79,x
        inc     $7D
        rts
