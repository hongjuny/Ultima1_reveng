; $9958-$99BC: locate an object at the current map cell and remove its slot.
; $997D is also called directly with X already holding the chosen slot.
.setcpu "6502"
.segment "CODE"

done:   rts
lookup: ldx     $00
        ldy     $01
        cpx     #$40
        bcs     done
        cpy     #$40
        bcs     done
        stx     $6C
        tya
        ora     $7E70
        ldx     $7EF6
scan:   dex
        bmi     done
        cmp     $7F47,x
        bne     scan
        ldy     $7EF7,x
        cpy     $6C
        bne     scan
remove: lda     $7F47,x
        and     #$C0
        cmp     $7E70
        bne     no_restore
        jsr     $98FA
        lda     $7FE7,x
        sta     ($72),y
no_restore:
        lda     $7F97,x
        sta     $60
        stx     $6C
        dec     $7EF6
        bne     finish
        rts
shift:  lda     $7EF8,x
        sta     $7EF7,x
        lda     $7F48,x
        sta     $7F47,x
        lda     $7F98,x
        sta     $7F97,x
        lda     $7FE8,x
        sta     $7FE7,x
        lda     $B601,x
        sta     $B600,x
        inx
finish: cpx     $7EF6
        bcc     shift
        ldx     $6C
        lda     $60
        rts
