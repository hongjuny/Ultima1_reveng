; Monster damage bound and rejection draw at $9A95-$9ADB.
; The accepted random value receives +1 as the damage amount.
.setcpu "6502"
.segment "CODE"

damage_roll:
        ldy     $A506
        sty     $A4F2
        lda     #$00
        sta     $A4F3
        sta     $A4F1
        lda     $A60D,y
        ldy     $A4FE
        jsr     $9CBC
draw:   jsr     $15B9
        sta     $A4F0
        lda     $A4F1
        beq     compare
        jsr     $15B9
        sta     $A4F1
compare:
        lda     $A4F0
        cmp     $A4F2
        lda     $A4F1
        sbc     $A4F3
        bcs     draw
        lda     $A4F0
        clc
        adc     #$01
        sta     $A4F2
        lda     $A4F1
        adc     #$00
        sta     $A4F3
