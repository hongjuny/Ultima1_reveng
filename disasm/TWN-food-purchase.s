; A town shop's 16-bit cost check, payment, and food credit, $932F-$9364.
.setcpu "6502"
.segment "CODE"

check_funds:
        lda     $7ED4
        cmp     $72
        lda     $7ED5
        sbc     $73
        bcs     pay_and_credit_food
        jmp     $9236

pay_and_credit_food:
        lda     $7ED4
        sec
        sbc     $72
        sta     $7ED4
        lda     $7ED5
        sbc     $73
        sta     $7ED5
        lda     $7EE5
        clc
        adc     $AA69
        sta     $7EE5
        lda     $7EE6
        adc     $AA6A
        sta     $7EE6
        jsr     $9E3B
