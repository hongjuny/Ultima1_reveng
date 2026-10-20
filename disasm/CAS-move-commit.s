; Castle accepted movement and turn update at $8C29-$8C4B.
.setcpu "6502"
.segment "CODE"

commit_move:
        ldx     $00
        ldy     $01
        lda     #$20
        jsr     $9BA8
        ldx     $0C
        stx     $00
        ldy     $0D
        sty     $01
        lda     #$7B
        jsr     $9BA8
        ldy     #$01
        lda     #$10
        jsr     $82E4
        jsr     $15D1
        jmp     $836E
