; GEN class input A–D, $8DEA-$8DFA.
.setcpu "6502"
.segment "CODE"

class_choice:
        jsr     $15BF
        cmp     #$41
        bcc     class_choice
        cmp     #$45
        bcs     class_choice
        sec
        sbc     #$40
        sta     $7ED8
