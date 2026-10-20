; Space command handler at $8A76-$8A7C. Shared routine performs the update.
.setcpu "6502"
.segment "CODE"

space_command:
        ldy     #$05
        lda     #$50
        jmp     $82E2
