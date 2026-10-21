; $9CBC-$9CD1: add A to the 16-bit bound Y times.
; DNG uses this to form depth + monster-scale[depth] * actor slot.
.setcpu "6502"
.segment "CODE"

add_actor_scale:
        sta     $A4F0
loop:   lda     $A4F2
        clc
        adc     $A4F0
        sta     $A4F2
        bcc     no_carry
        inc     $A4F3
no_carry:
        dey
        bne     loop
        rts
