; Direction negation and candidate coordinate at $A432-$A448.
.setcpu "6502"
.segment "CODE"

negate:
        eor     #$FF
        clc
        adc     #$01
        rts

candidate:
        lda     $A4E8
        clc
        adc     $A4EC
        tax
        lda     $A4E9
        clc
        adc     $A4ED
        tay
        rts
