; $9936-$9970: try candidate x/y movement, commit free cell, return carry.
.setcpu "6502"
.segment "CODE"

        lda     #$02
        jsr     $8254
        beq     try_y
        lda     $04
        beq     try_y
        jsr     $9D98
        tay
        beq     moved
try_y:
        lda     $05
        beq     try_x
        jsr     $9D74
        tay
        beq     moved
try_x:
        lda     $04
        beq     blocked
        jsr     $9D98
        tay
        bne     blocked
moved:
        jsr     $9C93
        lda     $B62C
        sta     $B628
        lda     $B62D
        sta     $B629
        jsr     $9C64
        clc
        rts
blocked:
        sec
        rts
