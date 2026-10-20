; MI.U1 load branch at $0B50-$0B69. Filename is inline data.
.setcpu "6502"
.segment "CODE"

maybe_load_game:
        cmp     #$9B
        beq     wait_next_key
        bit     $C055
        jsr     $B70C
        .byte   "MI.U1", $00
        rts
wait_next_key:
        lda     $C000
        bpl     wait_next_key
        bit     $C010
        rts
