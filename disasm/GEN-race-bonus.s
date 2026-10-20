; GEN race-dependent attribute bonuses, $8CFA-$8D3B.
; $7ED6 is 1–4 for choices A–D. The last path is the D case.
.setcpu "6502"
.segment "CODE"

apply_race_bonus:
        lda     $7ED6
        cmp     #$01
        bne     check_second_race
        lda     $7ED2
        clc
        adc     #$05
        sta     $7ED2
        .byte   $D0, $30       ; BNE $8D3C, outside this fragment
check_second_race:
        cmp     #$02
        bne     check_third_race
        lda     $7ECA
        clc
        adc     #$05
        sta     $7ECA
        .byte   $D0, $21       ; BNE $8D3C
check_third_race:
        cmp     #$03
        bne     fourth_race
        lda     $7EC8
        clc
        adc     #$05
        sta     $7EC8
        .byte   $D0, $12       ; BNE $8D3C
fourth_race:
        lda     $7ED0
        clc
        adc     #$0A
        sta     $7ED0
        lda     $7EC8
        sec
        sbc     #$05
        sta     $7EC8
