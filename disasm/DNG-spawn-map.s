; $9C82-$9C99: overlay selected slot at its accepted position.
.setcpu "6502"
.segment "CODE"

        ldx     $A4FE
        jsr     $9C9B
        lda     $A4FE
        asl     a
        asl     a
        asl     a
        asl     a
        jsr     $A41F
        dec     $A4EE
        beq     finished
        jmp     $9C11
finished:
