; Shared death path's zeroing of two-byte player fields at $888D-$88A0.
.setcpu "6502"
.segment "CODE"

zero_on_death:
        lda     #$00
        sta     $7ED4
        sta     $7ED5
        sta     $7EE5
        sta     $7EE6
        sta     $7EC6
        sta     $7EC7
