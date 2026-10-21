; $8254-$8265: draw a byte and reduce it modulo the input bound.
.setcpu "6502"
.segment "CODE"

        sta     $69
        jsr     $15B9
reduce:
        cmp     $69
        bcc     done
        sbc     $69
        bcs     reduce
done:
        cmp     #$00
        sta     $69
        rts
