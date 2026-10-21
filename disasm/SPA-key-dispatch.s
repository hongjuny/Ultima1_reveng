; $8A5F-$8A79: space mode key read, shared lookup, and resource gate.
.setcpu "6502"
.segment "CODE"

read_key:
        jsr     $15C2
        .byte   $F0, $4F    ; BEQ $8AB3
        jsr     $A1BD
        jsr     $82A2
        .byte   $B0, $47    ; BCS $8AB3
        cpx     #$08
        .byte   $B0, $34    ; BCS $8AA4
        lda     $7EE9
        ora     $7EEA
        .byte   $D0, $2C    ; BNE $8AA4
        jsr     $8119
