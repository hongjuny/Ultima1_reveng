; Castle left-key entry and x=0 exit test at $8AA8-$8AC0.
.setcpu "6502"
.segment "CODE"

left_key:
        ldx     #$FF
        ldy     #$00
movement:
        lda     $00
        beq     edge
move_inside:
        jmp     $8C00
edge:
        cpx     #$FF
        bne     move_inside
        lda     $B6BD
        cmp     #$05
        bcc     blocked_exit
        jmp     $8BFD
blocked_exit:
