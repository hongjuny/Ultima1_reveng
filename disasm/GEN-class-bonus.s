; GEN class-dependent attribute bonuses, $8E12-$8E53.
; $7ED8 is 1–4 for Fighter, Cleric, Wizard, Thief.
.setcpu "6502"
.segment "CODE"

apply_class_bonus:
        lda     $7ED8
        cmp     #$01
        bne     check_cleric
        lda     $7EC8
        clc
        adc     #$0A
        sta     $7EC8
        lda     $7ECA
        clc
        adc     #$0A
        sta     $7ECA
        .byte   $D0, $27       ; BNE $8E54, outside this fragment
check_cleric:
        cmp     #$02
        bne     check_wizard
        lda     $7ED0
        clc
        adc     #$0A
        sta     $7ED0
        .byte   $D0, $18       ; BNE $8E54
check_wizard:
        cmp     #$03
        bne     thief
        lda     $7ED2
        clc
        adc     #$0A
        sta     $7ED2
        .byte   $D0, $09       ; BNE $8E54
thief:
        lda     $7ECA
        clc
        adc     #$0A
        sta     $7ECA
