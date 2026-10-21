; $1C39-$1D63: outdoor map raster and animation before keyboard latch.
; Returns by falling through into the separately reviewed $1D64-$1D7E.
; $1CEB/$1CEC and $1CEE/$1CEF are operands patched by this routine.
.setcpu "6502"
.segment "CODE"

draw_outdoor:
        lda     #$08
        sta     $6B
        sec
        lda     $00
        sbc     #$09
        sta     $6C
        sec
        lda     $01
        sbc     #$04
        sta     $6D
next_tile_row:
        lda     #$10
        sta     $69
        lda     #$00
        sta     tile_source_low
        lda     #$0C
        sta     tile_source_high
        lda     $C000
        bpl     check_world_row
        jsr     $1D69
check_world_row:
        lda     $6D
        cmp     #$40
        bcs     clear_tile_row
        lsr     a
        sta     $73
        lda     #$00
        ror     a
        lsr     $73
        ror     a
        sta     $72
        lda     $73
        adc     #$60
        sta     $73
        ldx     #$00
        ldy     $6C
tile_loop:
        cpy     #$40
        bcc     read_tile
        lda     #$00
        beq     stage_tile
clear_tile_row:
        ldx     #$25
clear_tile:
        lda     #$01
        sta     $81,x
        dex
        lda     #$00
        sta     $81,x
        dex
        bpl     clear_tile
        bmi     raster_row
read_tile:
        lda     ($72),y
        and     #$7E
        cmp     #$20
        bcc     stage_tile
        cmp     #$59
        bcs     stage_tile
        stx     $6E
        sta     $6F
        inc     $1769
        ldx     $1769
        lda     $B700,x
        and     #$02
        adc     $6F
        ldx     $6E
stage_tile:
        sta     $81,x
        inx
        clc
        adc     #$01
        sta     $81,x
        inx
        iny
        cpx     #$26
        bcc     tile_loop
raster_row:
        lda     $6D
        inc     $6D
        cmp     $01
        bne     next_scanline
        ldy     $1582
        sty     $93
        iny
        sty     $94
next_scanline:
        ldy     $6B
        inc     $6B
        clc
        lda     $1200,y
        adc     #$01
        sta     video_low
        lda     $12C0,y
        eor     $7F
        sta     video_high
        ldx     #$25
pixel_loop:
        ldy     $81,x
        .byte   $B9             ; LDA absolute,Y, patched tile-source operand
tile_source_low:
        .byte   $00
tile_source_high:
        .byte   $0C
        .byte   $9D             ; STA absolute,X, patched video operand
video_low:
        .byte   $00
video_high:
        .byte   $20
        dex
        bpl     pixel_loop
        clc
        lda     tile_source_low
        adc     #$60
        sta     tile_source_low
        bcc     next_source_row
        inc     tile_source_high
next_source_row:
        dec     $69
        bne     next_scanline
        lda     $6B
        cmp     #$98
        bcs     finish_raster
        jmp     next_tile_row
finish_raster:
        jsr     $1637
        dec     $1766
        bne     phase_two
        lda     #$02
        sta     $1766
        ldy     #$00
        jsr     $1A85
phase_two:
        dec     $1767
        bne     phase_three
        lda     #$03
        sta     $1767
        ldx     $0C69
        ldy     $0CC9
        sty     $0C69
        stx     $0CC9
phase_three:
        dec     $1768
        bne     swap_always
        lda     #$02
        sta     $1768
        ldx     $0D2C
        ldy     $0D8C
        sty     $0D2C
        stx     $0D8C
swap_always:
        ldx     $0CD9
        ldy     $0D39
        sty     $0CD9
        stx     $0D39
        ldx     $0CD8
        ldy     $0D38
        sty     $0CD8
        stx     $0D38
