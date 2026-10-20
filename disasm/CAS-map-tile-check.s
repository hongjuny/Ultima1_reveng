; Castle tile lookup and passability threshold at $9BD9-$9BFD.
; The absolute operand below is patched from the row-pointer tables on each call.
.setcpu "6502"
.segment "CODE"

tile_check:
        cpx     #$26            ; columns 0-37
        bcc     row_in_bounds
out_of_bounds:
        lda     #$60
        clc
        rts
row_in_bounds:
        cpy     #$12            ; rows 0-17
        bcs     out_of_bounds
        lda     $9EA8,y
        clc
        adc     #$00
        sta     tile_operand
        lda     $9EBA,y
        adc     #$B4
        sta     tile_operand+1
        .byte   $BD             ; LDA absolute,X; operand is self-modified
tile_operand:
        .word   $FFFF
        cmp     #$60
        bcs     passable
        rts                     ; tile below $60 leaves carry clear
passable:
