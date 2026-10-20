; GEN previous-game choice: load and validate U1.VARS, $8A10-$8A2B.
; $B721 consumes inline destination $6000 and path pointer $7E38.
.setcpu "6502"
.segment "CODE"

load_previous_character:
        lda     #$62
        jsr     $15B0
        jsr     $B721
        .byte   $00, $60, $38, $7E
        .byte   $B0, $0E       ; BCS $8A2C, read failure
        lda     $6000
        cmp     #$CA
        .byte   $D0, $07       ; BNE $8A2C, invalid header
        lda     $6001
        cmp     #$01
        .byte   $F0, $2F       ; BEQ $8A5B, accepted record
