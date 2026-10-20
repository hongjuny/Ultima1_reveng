; Castle collision result handling at $9BC0-$9BD8.
.setcpu "6502"
.segment "CODE"

check_collision:
        jsr     $9BD9
        bcs     tile_allowed
        rts
tile_allowed:
        lda     $00
        cmp     $72
        bne     free
        lda     $01
        cmp     $73
        bne     free
        lda     #$2F
        clc
        rts
free:
        tya
        sec
        rts
