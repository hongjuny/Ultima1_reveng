; $9666-$966F: current tile $08 ascends; other accepted stair
; codes continue to the deeper-level path at $972C.
.setcpu "6502"
.segment "CODE"

stair_gate:
        lda     $A4F2
        cmp     #$08
        beq     ascend
        jmp     $972C
ascend:
