; Food-shop price per ten-food pack from player attribute $7ED2, $9257-$926E.
.setcpu "6502"
.segment "CODE"

food_pack_price:
        ldx     #$05
        lda     $7ED2
price_step:
        sec
        sbc     #$14
        bcc     price_ready
        dex
        bne     price_step
        inx
price_ready:
        stx     $AA6B
        txa
        clc
        adc     #$30
        sta     $928A
