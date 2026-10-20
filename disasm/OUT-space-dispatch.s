; Outdoor space entry selection at $8D6E-$8D72.
.setcpu "6502"
.segment "CODE"

select_space:
        lda     #$14
        jmp     $8EFA
