; $8062-$8085: send a character to STUPH or interpret layout controls.
.setcpu "6502"
.segment "CODE"

emit:
        jsr     $15B0
        inc     $24
return:
        rts
control:
        and     #$7F
        cmp     #$7C
        bcc     emit
        .byte   $F0, $19    ; BEQ $8089
        cmp     #$7E
        beq     advance
        cmp     #$7D
        bne     return
        lda     $24
        cmp     #$02
        bcc     reset_column
advance:
        jsr     $8089
reset_column:
        lda     #$01
        sta     $24
        rts
