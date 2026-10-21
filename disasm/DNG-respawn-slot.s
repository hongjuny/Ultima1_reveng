; $93C6-$93DC: choose an inactive slot and reactivate it after a kill.
.setcpu "6502"
.segment "CODE"

choose_slot:
        jsr     $15B9
        and     #$07
        beq     choose_slot
        cmp     #$06
        bcs     choose_slot
        sta     $A4FE
        tax
        lda     $A508,x
        beq     choose_slot
        dec     $A508,x
