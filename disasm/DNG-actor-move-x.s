; $997F-$99A9: horizontal monster move after reading the old map cell.
; A carries the old cell; the map writer stores A at (X,Y).
.setcpu "6502"
.segment "CODE"

restore_departed_cell:
        pla
        and     #$0F
        jsr     $A41F
        ldx     $A4FE
        lda     $A4EA
        sta     $A50E,x
        jsr     $9C9B
        jsr     $9D32
        sta     $A4F2
        ldx     $A4FE
        jsr     $9C9B
        lda     $A4FE
        asl     a
        asl     a
        asl     a
        asl     a
        ora     $A4F2
        jsr     $A41F
