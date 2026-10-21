; $8D36-$8D98: place stairs by depth parity, with level 1/10 overrides.
; Map writer $A41F receives value in A and (x,y) in X,Y.
.setcpu "6502"
.segment "CODE"

place_stairs:
        lda     #$00
        ldx     #$01
        ldy     #$02
        jsr     $A41F
        lda     $A506
        and     #$01
        bne     odd_level
        lda     #$07
        ldx     #$07
        ldy     #$03
        jsr     $A41F
        lda     #$08
        ldx     #$03
        ldy     #$07
        jsr     $A41F
        jmp     special_levels
odd_level:
        lda     #$08
        ldx     #$07
        ldy     #$03
        jsr     $A41F
        lda     #$07
        ldx     #$03
        ldy     #$07
        jsr     $A41F
special_levels:
        lda     $A506
        cmp     #$0A
        bne     first_level
        lda     #$00
        ldx     #$07
        ldy     #$03
        jsr     $A41F
first_level:
        lda     $A506
        cmp     #$01
        bne     done
        lda     #$08
        ldx     #$01
        ldy     #$01
        jsr     $A41F
        lda     #$00
        ldx     #$07
        ldy     #$03
        jsr     $A41F
done:
        jmp     $9BED
