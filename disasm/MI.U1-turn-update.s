; Shared decimal-mode resource/time update at $82E2-$8330.
; The leading BCS targets the operand byte at $831D; preserve its raw bytes.
.setcpu "6502"
.segment "CODE"

turn_update:
        clc
        .byte   $B0, $38
        sty     $7E4F
        sta     $7E50
        bcc     update
        lda     #$00
        jsr     $15CE
update:
        sed
        sec
        lda     $7EE4
        sbc     $7E4F
        sta     $7EE4
        bcs     add_time
        lda     $7EE5
        ora     $7EE6
        beq     add_time
        lda     $7EE5
        bne     dec_food_low
        dec     $7EE6
dec_food_low:
        dec     $7EE5
add_time:
        clc
        lda     $7EDA
        adc     $7E50
        sta     $7EDA
        bcs     carry_to_high
        cld
        rts
carry_to_high:
        sed
        sec
        ldx     #$00
carry_loop:
        lda     $7EDB,x
        adc     #$00
        sta     $7EDB,x
        inx
        bcs     carry_loop
        cld
        rts
