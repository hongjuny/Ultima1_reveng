; Dungeon map byte at $9D32-$9D48. Rows have stride 11 and
; the 121-byte working map begins at $B099.
.setcpu "6502"
.segment "CODE"

read_map:
        txa
        cpy     #$00
row:    beq     found
        clc
        adc     #$0B
        dey
        jmp     row
found:  tax
        lda     $B099,x
        rts

read_low_nibble:
        jsr     read_map
        and     #$0F
        rts
