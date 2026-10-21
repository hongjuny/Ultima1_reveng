; $1DD6-$1DF0, called by both bounded and outdoor input paths.
; The immediate operand at $1DED is modified by the store at $1DE9.
; X/Y are saved for restoration by the common return at $1DCD.
.setcpu "6502"
.segment "CODE"

input_prelude:
        stx     $1764
        sty     $1765
        jsr     $1670
        ldx     glyph_operand
        dex
        cpx     #$7C
        bcs     keep_glyph
        ldx     #$7F
keep_glyph:
        stx     glyph_operand
        .byte   $A9
glyph_operand:
        .byte   $7C
        jsr     $1A1D
