; Outdoor input poll at $8A6A-$8A75. X bounds the number of polls.
.setcpu "6502"
.segment "CODE"

poll_input:
        ldx     #$80
retry:
        jsr     $15C5
        bne     done
        dex
        bne     retry
done:
        tax
        rts
