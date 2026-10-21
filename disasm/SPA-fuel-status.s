; $A154-$A1BC: subtract a cost from Fuel ($7EE9/$7EEA), then redraw status.
; The status order after the "Shld|Fuel" label is Shield, Fuel, another
; resource, and Coin. The third resource's meaning needs a separate trace.
.setcpu "6502"
.segment "CODE"

        sta     $A7
        sec
        lda     $7EE9
        sbc     $A7
        sta     $7EE9
        bcs     no_high_borrow
        dec     $7EEA
        lda     $7EEA
        cmp     #$FF
        bne     redraw
        lda     #$00
        sta     $7EE9
        sta     $7EEA
        beq     zero_motion
no_high_borrow:
        lda     $7EE9
        ora     $7EEA
        bne     redraw
        lda     #$00
zero_motion:
        sta     $928E
redraw:
        jsr     $83B4
        jsr     $15A1
        sta     $8249
        lda     #$24
        sta     $20
        lda     #$04
        sta     $21
        lda     $7EEC
        ldx     $7EEB
        jsr     $8355
        lda     $7EEA
        ldx     $7EE9
        jsr     $8355
        lda     $7EE8
        ldx     $7EE7
        jsr     $8355
        lda     $7ED5
        ldx     $7ED4
        jsr     $8207
        jsr     $1598
        jmp     $83A9
