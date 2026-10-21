; $9437-$9446: encode actor slot in the map high nibble at spawn.
; $9C9B loads this slot's coordinates; writer $A41F stores A at (X,Y).
.setcpu "6502"
.segment "CODE"

write_actor_slot:
        ldx     $A4FE
        jsr     $9C9B
        lda     $A4FE
        asl     a
        asl     a
        asl     a
        asl     a
        jsr     $A41F
