; GEN sex input A/B, $8D72-$8D82.
; A becomes 0 at $7EB7; B becomes 1.
.setcpu "6502"
.segment "CODE"

sex_choice:
        jsr     $15BF
        cmp     #$41
        bcc     sex_choice
        cmp     #$43
        bcs     sex_choice
        sec
        sbc     #$41
        sta     $7EB7
