; Castle guard damage bound and nonzero roll at $998F-$99A5.
.setcpu "6502"
.segment "CODE"

guard_damage:
        lda     $7EC7
        asl     a
        asl     a
        clc
        adc     #$14
        sta     $72
retry:
        jsr     $15B9
        cmp     #$00
        beq     retry
        cmp     $72
        bcs     retry
        sta     $73
