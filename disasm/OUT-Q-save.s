; $92CA-$92DF: outdoor Q writes the live 458-byte player record.
.setcpu "6502"
.segment "CODE"

        ldx     $00
        ldy     $01
        stx     $7E73       ; persist current outdoor X
        sty     $7E74       ; persist current outdoor Y
        jsr     $83B4
        jsr     $B724       ; save helper consumes six inline bytes
        .word   $7E6D       ; source
        .word   $01CA       ; length (458)
        .word   $7E38       ; path pointer: /U1.PLAYER/U1.VARS
