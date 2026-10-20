; Castle guard damage applied to player HP at $99CB-$99E0.
.setcpu "6502"
.segment "CODE"

apply_damage:
        lda     $7EC6
        sec
        sbc     $73
        sta     $7EC6
        lda     $7EC7
        sbc     #$00
        sta     $7EC7
        bcs     survived
        jmp     $8A41
survived:
