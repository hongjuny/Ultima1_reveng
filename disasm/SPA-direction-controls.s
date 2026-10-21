; $8FAD-$9099: space Up/Down travel, coordinate clamp, Right/Left turn.
; The three bytes after each JSR $8119 are inline display arguments.
; $8FF4-$8FFB and $9046-$904D are direction delta tables, not code.
.setcpu "6502"
.segment "CODE"

up:
        lda     $9240
        beq     up_move
        lda     #$00
        jsr     $15CB
        jmp     $8BB5
up_move:
        ldx     $923F
        clc
        lda     $928A
        adc     up_x_delta,x
        jsr     clamp_position
        sta     $928A
        clc
        lda     $928B
        adc     up_y_delta,x
        jsr     clamp_position
        sta     $928B
        lda     #$00
        jsr     $15CB
        lda     #$08
        adc     $928E
        and     #$7F
        sta     $928E
        lda     #$05
        jsr     $A154
        jsr     $8119
        .byte   $7C,$0E,$00
        jmp     $8AB3

up_x_delta:
        .byte   $00,$02,$00,$FE
up_y_delta:
        .byte   $FF,$00,$01,$00

clamp_position:
        cmp     #$80
        bcs     negative_side
        cmp     #$09
        bcc     clamp_done
        lda     #$08
        rts
negative_side:
        cmp     #$F8
        bcs     clamp_done
        lda     #$F8
clamp_done:
        rts

down:
        ldx     $923F
        clc
        lda     $928A
        adc     down_x_delta,x
        jsr     clamp_position
        sta     $928A
        clc
        lda     $928B
        adc     down_y_delta,x
        jsr     clamp_position
        sta     $928B
        lda     #$00
        jsr     $15CB
        lda     #$00
        sta     $928E
        sta     $9240
        lda     #$05
        jsr     $A154
        jsr     $8119
        .byte   $7C,$0E,$00
        jmp     $8AB3

down_x_delta:
        .byte   $00,$FE,$00,$02
down_y_delta:
        .byte   $01,$00,$FF,$00

right:
        lda     $9240
        beq     right_turn
        jmp     $8BB5
right_turn:
        lda     $923F
        clc
        adc     #$01
        and     #$03
        sta     $923E
        lda     #$00
        sta     $928E
        lda     #$02
        jsr     $A154
        jsr     $8119
        .byte   $7C,$0E,$00
        jmp     $8AB8

left:
        lda     $9240
        beq     left_turn
        jmp     $8BB5
left_turn:
        ldx     $923F
        dex
        bpl     left_store
        ldx     #$03
left_store:
        stx     $923E
        lda     #$00
        sta     $928E
        lda     #$02
        jsr     $A154
        jsr     $8119
        .byte   $7C,$0E,$00
        jmp     $8AB8
