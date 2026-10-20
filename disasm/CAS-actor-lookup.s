; Castle map actor lookup at $9BFE-$9C22.
; The caller has already accepted the underlying map tile.
.setcpu "6502"
.segment "CODE"

actor_lookup:
        stx     $72
        sty     $73
        ldx     #$0F
        tay
scan_actor:
        lda     $B6BC,x
        cmp     $72
        bne     next_actor
        lda     $B6CC,x
        cmp     $73
        bne     next_actor
        stx     $9E36
        lda     $B6AC,x
        clc
        adc     #$30
        rts
next_actor:
        dex
        bpl     scan_actor
        tya
        sec
        rts
