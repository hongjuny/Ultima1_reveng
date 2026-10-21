; $8119-$8143: consume bytes inline after the caller's JSR.
.setcpu "6502"
.segment "CODE"

print_inline:
        pla
        sta     $8040
        pla
        sta     $8041
next_byte:
        jsr     $8037
        beq     done
        cmp     #$7F
        beq     skip_columns
        jsr     $8068
        jmp     next_byte
skip_columns:
        jsr     $8037
        clc
        adc     $24
        sta     $24
        jmp     next_byte
done:
        lda     $8041
        pha
        lda     $8040
        pha
        rts
