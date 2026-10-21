; Commit a candidate dungeon position at $8EBE-$8ECD.
; $A438 computes X/Y; tile code $02 continues to the stair handler.
.setcpu "6502"
.segment "CODE"

commit_move:
        pha
        jsr     $A438
        stx     $A4E8
        sty     $A4E9
        pla
        cmp     #$02
        beq     stairs
        rts
stairs:
