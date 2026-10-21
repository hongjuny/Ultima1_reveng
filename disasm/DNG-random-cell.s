; $8D20-$8D30: choose cell code $05/$06 from shared random-byte bit 0.
; Writer $A41F receives generated coordinates in X,Y.
.setcpu "6502"
.segment "CODE"

random_cell:
        jsr     $15B9
        and     #$01
        clc
        adc     #$05
        ldx     $A4EE
        ldy     $A4EF
        jsr     $A41F
