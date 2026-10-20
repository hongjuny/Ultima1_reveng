; Castle bounded key poll at $8A25-$8A30.
.setcpu "6502"
.segment "CODE"

poll:
        ldx     #$80
try_key:
        jsr     $15C2
        bne     got_key
        dex
        bne     try_key
got_key:
        tax
        rts
