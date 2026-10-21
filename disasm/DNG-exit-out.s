; $9716-$9727: leave the dungeon through the common OUT selector.
.setcpu "6502"
.segment "CODE"

exit_to_out:
        jsr     $836E
        jsr     $83B4
        jsr     $8151
        jsr     $83A9
        jsr     $158F
        jmp     $88FB
