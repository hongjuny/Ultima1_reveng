; $1AB2-$1B01: nine effect return-address pointers and common sound dispatch.
; Even A values 0..16 index the table. Each pointer is target address minus one
; because RTS adds one after popping the synthetic return address.
.setcpu "6502"
.segment "CODE"

effect_return_addresses:
        .word   $1BF3,$1BED,$1BCD,$1B4D,$1BBC,$1B47,$1BA8,$1B31,$1B41

sound_dispatch:
        stx     $69
        tax
        lsr     a
        bcs     no_sound
        cpx     #$12
        bcs     no_sound
        lda     $1581
        beq     no_sound
        lda     $1580
        beq     call_effect
        bit     $175B
        bvs     call_effect
        lda     $C036
        and     #$1F
        pha
        sta     $C036
        jsr     call_effect
        pla
        ora     #$80
        sta     $C036
        rts

call_effect:
        php
        sei
        jsr     dispatch_by_rts
        plp
        rts

dispatch_by_rts:
        lda     effect_return_addresses+1,x
        pha
        lda     effect_return_addresses,x
        pha
no_sound:
        ldx     $69
        rts
