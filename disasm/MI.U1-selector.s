; Reviewed MI.U1 module selector, original address $88F8-$893E.
; Link this segment at $88F8. Inline filename/pointer data is intentional.
.setcpu "6502"
.segment "CODE"

outdoor_setup:
        jsr     $8870
outdoor_selector:
        lda     #$04
module_selector:
        ldx     #$FF
        txs
        cmp     #$19
        bcs     load_gen
        tax
        bne     copy_name
load_gen:
        jsr     $B703
        .byte   "GEN", $00
        bcs     load_gen
        jmp     $8956
copy_name:
        ldy     #$00
copy_loop:
        lda     $7E16,x
        sta     $7E16,y
        inx
        iny
        asl     a
        bne     copy_loop
load_other:
        jsr     $8414
        jsr     $B736
        .word   $7E16
        jsr     $1589
        jsr     $7DCC
        bcs     load_other
        jsr     $7E05
        jsr     $8331
        jsr     $8151
        jsr     $83A9
        jmp     $8956
