; OUT resurrection setup at $89E8-$8A1C.
.setcpu "6502"
.segment "CODE"

resurrection_setup:
        ldx     #$0A
pause:
        jsr     $15E9
        dex
        bpl     pause
        jsr     $9461
        stx     $00
        sty     $01
        jsr     $9691
        lda     #$00
        ldx     $7E7C
        beq     clear_table
        sta     $7E7C
        ldy     $7E9E,x
        beq     clear_table
        dec     $7E9E,x
clear_table:
        ldx     #$0F
clear_entry:
        sta     $7E83,x
        dex
        bne     clear_entry
        sta     $7E7B
        sta     $7E7A
        sta     $7E79
