; $1D64-$1D7E: read Apple II keyboard latch into the shared input buffer.
.setcpu "6502"
.segment "CODE"

read_latch:
        lda     $C000
        bpl     done
        cmp     #$A0
        bne     append
        ldx     #$00
        stx     $78
append:
        ldx     $78
        cpx     #$04
        bcs     done
        sta     $74,x
        inc     $78
        bit     $C010
done:
        rts
