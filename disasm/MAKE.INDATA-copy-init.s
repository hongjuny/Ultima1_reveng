; MAKE.INDATA $1EFD-$1F41: page copy helper and first entry's setup.
; At entry, A is the destination high byte, X/Y the source address, and $FF
; is the number of pages. This copies file payload away from $2000 and $27BD
; before the original load range is reused.
.setcpu "6502"
.segment "CODE"

copy_pages:
        stx     $06
        sty     $07
        sta     $09
        ldy     #$00
        sty     $08
copy_next:
        lda     ($06),y
        sta     ($08),y
        iny
        bne     copy_next
        inc     $07
        inc     $09
        dec     $FF
        bne     copy_next
        rts

initial_setup:
        ldx     #$00
        ldy     #$20
        lda     #$08
        sta     $FF
        lda     #$87
        jsr     copy_pages
        ldx     #$BD
        ldy     #$27
        lda     #$26
        sta     $FF
        lda     #$60
        jsr     copy_pages
        lda     #$EC
        sta     $00
        lda     #$49
        sta     $01
        jsr     $1E03
        jsr     $8700
        jsr     $1F5C
