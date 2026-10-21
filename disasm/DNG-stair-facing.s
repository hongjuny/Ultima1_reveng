; $963F-$9646: require a nonzero vertical facing component for $07/$08.
; The fallthrough prints an inline refusal message before returning.
.setcpu "6502"
.segment "CODE"

stair_facing_gate:
        lda     $A4ED
        bne     *+$24         ; $9666 when linked at $963F
        jsr     $8119
