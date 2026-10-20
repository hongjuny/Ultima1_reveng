; Input/timer loop at $1039-$1056.
.setcpu "6502"
.segment "CODE"

intro_loop_start:
        lda     #$00
        ldx     #$20
wait_loop:
        bit     $C000
        bmi     key_pressed
        jsr     $0E23
        dex
        bne     wait_loop
        jmp     $0F41
key_pressed:
        lda     $C000
        bit     $C010
        jsr     $0B50
        jmp     wait_loop
