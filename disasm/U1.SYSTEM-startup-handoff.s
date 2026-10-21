; Reviewed U1.SYSTEM startup filename handling and low-memory transfer.
; Original address $21D6-$2222. The two bytes after JSR $B72A are inline data.
.setcpu "6502"
.segment "CODE"

startup_filename:
        lda     #$00
        sta     $2007,y
        lda     #$C7
        jsr     $B700
        lda     $BA79
        bne     copy_startup_name
        lda     $2007
        and     #$7F
        cmp     #$2F
        beq     copy_startup_name
        ldy     $0280
find_separator:
        lda     $0280,y
        and     #$7F
        cmp     #$2F
        beq     found_separator
        dey
        bne     find_separator
found_separator:
        cpy     #$02
        bcc     copy_startup_name
        lda     #$00
        sta     $2047,y
copy_prefix:
        lda     $0280,y
        sta     $2046,y
        dey
        bne     copy_prefix
        jsr     $B72A
        .word   $2047
copy_startup_name:
        ldy     $2006
copy_name_loop:
        lda     $2006,y
        sta     $02C0,y
        dey
        bpl     copy_name_loop
        jmp     $0136
