; $8037-$8042: advance the inline-text pointer and read one byte.
.setcpu "6502"
.segment "CODE"

next_inline_byte:
        inc     $8040
        bne     load_byte
        inc     $8041
load_byte:
        .byte   $AD, $00, $02  ; LDA absolute, operands patched at $8040/$8041
        rts
