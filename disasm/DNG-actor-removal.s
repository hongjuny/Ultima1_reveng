; $93A7-$93C5: mark defeated slot inactive and restore its cell low nibble.
.setcpu "6502"
.segment "CODE"

        ldx     $A4F2
        stx     $A52E
        lda     #$01
        sta     $A508,x
        ldx     $A4EA
        ldy     $A4EB
        jsr     $9D32
        and     #$0F
        ldx     $A4EA
        ldy     $A4EB
        jsr     $A41F
