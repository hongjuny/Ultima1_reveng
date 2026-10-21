; $A41F-$A431 writes a generated cell to the 11-column map at $B099.
.setcpu "6502"
.segment "CODE"

write_map:
        pha
        txa
        cpy     #$00
row:    beq     found
        clc
        adc     #$0B
        dey
        jmp     row
found:  tay
        pla
        sta     $B099,y
        rts
