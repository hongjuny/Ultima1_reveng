; Outdoor location-to-overlay selector at $90FF-$9139.
.setcpu "6502"
.segment "CODE"

select_location:
        cmp     #$04
        bne     check_town
        lda     #$10
        bne     load_location
check_town:
        cmp     #$06
        bne     select_dungeon
        jsr     $9597
        ldx     $00
        ldy     $01
        dey
        jsr     $90B0
        sta     $7EB1
        iny
        dex
        jsr     $90B0
        sta     $7EB2
        inx
        inx
        jsr     $90B0
        sta     $7EB3
        dex
        iny
        jsr     $90B0
        sta     $7EB4
        lda     #$0C
        bne     load_location
select_dungeon:
        lda     #$08
load_location:
        jmp     $8EFA
