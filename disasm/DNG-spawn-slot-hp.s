; $9C11-$9C53: choose an inactive slot, activate it, and set its HP.
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
        lda     #$0A
        sta     $A4F2
        lda     #$00
        sta     $A4F3
        ldy     $A506
        lda     $A60D,y
        cmp     #$01
        beq     add_slot_hp
        jsr     $8254
add_slot_hp:
        ldy     $A4FE
        jsr     $9CBC
        ldx     $A4FE
        lda     $A4F2
        sta     $A51A,x
        lda     $A4F3
        sta     $A520,x
