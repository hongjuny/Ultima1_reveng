; $8E80-$8EA7: time-machine input dispatch with patched handler call.
.setcpu "6502"
.segment "CODE"

input_dispatch:
        jsr     $9815
        bne     key_ready
        jsr     $9808
        jsr     $9BDF
        jmp     $8E67
key_ready:
        jsr     $82A2
        .byte   $B0, $CB    ; BCS $8E5E
        lda     $8EA8,x
        sta     $8EA0
        lda     $8EA9,x
        sta     $8EA1
        .byte   $20, $1D, $84  ; JSR $841D, patched at $8EA0/$8EA1
        jsr     $8414
        jmp     $8E5E
