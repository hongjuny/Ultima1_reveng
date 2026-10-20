; GEN character-name input, $8E83-$8EED. The prompt begins at $8EEE.
; $9042 is the length; $7EB8-$7EC4 holds up to thirteen characters.
.setcpu "6502"
.segment "CODE"

name_key:
        jsr     $15BF
        ldx     $9042
        cmp     #$0D
        bne     check_delete
        txa
        beq     name_key        ; an empty name cannot be submitted
        dec     $25
        jsr     $93CC
        lda     #$0B
        sta     $24
        lda     #$03
        sta     $25
        jsr     $8837
        jmp     $8EEE          ; confirmation prompt, outside fragment

check_delete:
        cmp     #$08
        beq     delete
        cmp     #$7F
        bne     check_character
delete:
        dex
        bmi     name_key
        stx     $9042
        lda     #$00
        sta     $7EB8,x
        dec     $24
        jmp     name_key

check_character:
        cpx     #$00
        bne     later_character
        cmp     #$41
        bcc     name_key
        cmp     #$5B
        bcs     name_key
store_character:
        sta     $7EB8,x
        inc     $9042
        jsr     $8062
        jmp     name_key

later_character:
        cpx     #$0D
        bcs     name_key
        cmp     #$20
        bcc     name_key
        cmp     #$41
        bcc     store_character
        cmp     #$5B
        bcs     store_character
        ldy     $7EB7,x       ; previous character: $7EB8 + (X - 1)
        cpy     #$20
        beq     store_character
        ora     #$20          ; lowercase A-Z unless preceded by space
        bne     store_character
