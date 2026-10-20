; GEN race input validation and selection, $8CD0-$8CE0.
.setcpu "6502"
.segment "CODE"

race_choice:
        jsr     $15BF
        cmp     #$41
        bcc     race_choice
        cmp     #$45
        bcs     race_choice
        sec
        sbc     #$40
        sta     $7ED6
