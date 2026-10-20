; GEN confirmation input and persistence call, $8F0F-$8F30.
; The six inline bytes after JSR $B724 are consumed by that helper.
.setcpu "6502"
.segment "CODE"

confirmation_key:
        jsr     $93CC
        jsr     $15BF
        jsr     $15B0
        cmp     #$59            ; Y
        beq     save_character
        cmp     #$4E            ; N
        .byte   $D0, $CE       ; BNE $8EEE, repeat prompt
        jmp     $8AC3          ; restart character generation

save_character:
        jsr     $B724
        .byte   $6D, $7E, $CA, $01, $38, $7E
        .byte   $B0, $03       ; BCS $8F31, error handling
        jmp     $895B          ; return to GEN entry flow
