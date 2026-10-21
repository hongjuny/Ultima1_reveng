; $972C-$9731: increment dungeon depth and print the descent message.
; The following bytes embed text and are outside this code fragment.
.setcpu "6502"
.segment "CODE"

descend:
        inc     $A506
        jsr     $8119
