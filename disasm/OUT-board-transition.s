; Reviewed OUT B-command transition gate, original $8D61-$8D8D.
; $7E7C holds the craft code selected from the current world tile.
.setcpu "6502"
.segment "CODE"

board_selected:
        jsr     $9A83
        lda     $7E7C
        cmp     #$06
        beq     select_space
        bcs     check_time_machine
        rts
select_space:
        lda     #$14
select_overlay:
        jmp     $8EFA
check_time_machine:
        lda     $7E75
        beq     reject
        lda     $7E76
        beq     reject
        lda     $7E77
        beq     reject
        lda     $7E78
        beq     reject
        lda     #$18
        bne     select_overlay
reject:
        jsr     $83B4
