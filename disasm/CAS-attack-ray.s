; Castle directional attack scan at $8CC9-$8CF6.
.setcpu "6502"
.segment "CODE"

next_tile:
        lda     $0C
        clc
        adc     $04
        sta     $0C
        tax
        lda     $0D
        clc
        adc     $05
        sta     $0D
        tay
        jsr     $9BC0
        php
        cmp     #$16
        bcc     reduce_range
        plp
        php
        bcs     reduce_range
        plp
        cmp     #$30
        bcc     miss
        cmp     #$36
        bcs     miss
        jmp     $8D08
reduce_range:
        plp
        dec     $9E35
        bne     next_tile
miss:
