; CAS pointer selection and three-page copy at $89BB-$89DF.
; This code patches the operands of source_read and dest_write.
.setcpu "6502"
.segment "CODE"

        pla
        asl     a
        tax
        lda     $4000,x
        sta     source_read+1
        lda     $4001,x
        sta     source_read+2
        ldy     #$03
        ldx     #$00
source_read:
        lda     $FFFF,x
dest_write:
        sta     $B400,x
        dex
        bne     source_read
        inc     source_read+2
        inc     dest_write+2
        dey
        bne     source_read
