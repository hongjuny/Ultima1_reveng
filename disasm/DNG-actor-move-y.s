; $99D6-$9A00: vertical monster move after reading the old map cell.
; Runtime-confirmed mirror of the observed horizontal path.
.setcpu "6502"
.segment "CODE"

restore_departed_cell:
        pla
        and     #$0F
        jsr     $A41F
        ldx     $A4FE
        lda     $A4EB
        sta     $A514,x
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
