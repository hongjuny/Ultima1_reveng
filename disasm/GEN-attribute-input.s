; GEN attribute allocation input, $8C00-$8C80.
; $9041 selects one of six two-byte-spaced values at $7EC8–$7ED2;
; $903F tracks unassigned points. Input codes are the values from $15BF.
.setcpu "6502"
.segment "CODE"

attribute_loop:
        jsr     $8FB1
        lda     #$63
        sta     $24
read_key:
        jsr     $15BF
        tay
        lda     $9041
        asl     a
        tax
        cpy     #$1B
        bne     check_decrease
        jmp     $895B
check_decrease:
        cpy     #$08
        bne     check_increase
        lda     $7EC6,x
        cmp     #$0A
        beq     attribute_loop
        dec     $7EC6,x
        inc     $903F
        bne     attribute_loop
check_increase:
        cpy     #$15
        bne     check_next
        lda     $903F
        beq     attribute_loop
        lda     $7EC6,x
        cmp     #$19
        bcs     attribute_loop
        inc     $7EC6,x
        dec     $903F
        bpl     attribute_loop
check_next:
        cpy     #$2F
        beq     advance
        cpy     #$0A
        bne     check_previous
advance:
        inc     $9041
        lda     $9041
        cmp     #$07
        bcc     attribute_loop
        lda     #$01
        sta     $9041
        beq     attribute_loop
check_previous:
        cpy     #$0D
        beq     retreat
        cpy     #$0B
        bne     check_space
retreat:
        dec     $9041
        bne     attribute_loop
        lda     #$06
        sta     $9041
        bne     attribute_loop
check_space:
        cpy     #$20
        bne     attribute_loop
        ldy     $903F
        beq     continue_character_creation
        jsr     $840F
        jmp     attribute_loop
continue_character_creation:
        sty     $9041
