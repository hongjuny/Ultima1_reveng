; $99BF-$99E6: Mondain hit damage = floor(player HP / 32) + random(0..19).
.setcpu "6502"
.segment "CODE"

        lda     $7EC6
        sta     $C3
        lda     $7EC7
        sta     $C4
        ldy     #$05
divide_hp:
        lsr     $C4
        ror     $C3
        dey
        bne     divide_hp
        lda     #$14
        jsr     $8254
        clc
        adc     $C3
        sta     $7E4B
        lda     $C4
        adc     #$00
        sta     $7E4C
        jmp     $9B15
