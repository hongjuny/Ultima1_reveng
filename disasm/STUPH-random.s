; Shared random-byte routine at $1DF1-$1E17.
; State occupies $1E18-$1E27; $15B9 jumps here.
.setcpu "6502"
.segment "CODE"

random_byte:
        clc
        lda     $1E27
        ldx     #$0E
mix:
        adc     $1E18,x
        sta     $1E18,x
        dex
        bpl     mix
        lda     $1E27
        clc
        adc     $1E18
        sta     $1E18
        ldx     #$0F
increment:
        inc     $1E18,x
        bne     done
        dex
        bpl     increment
done:
        lda     $1E18
        rts
