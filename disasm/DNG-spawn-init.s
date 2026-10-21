; $9C02-$9C10: mark slots 1–5 inactive, then request three actors.
.setcpu "6502"
.segment "CODE"

        ldx     #$05
        lda     #$01
mark_inactive:
        sta     $A508,x
        dex
        bne     mark_inactive
        lda     #$03
        sta     $A4EE
