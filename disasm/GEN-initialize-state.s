; GEN new-character state copy, $8AEA-$8B24.
; The absolute operands of LDA and STA are rewritten as the copy advances.
.setcpu "6502"
.segment "CODE"

initialize_character_state:
        jsr     $93CC
        lda     #$6F
        sta     copy_destination+1
        lda     #$7E
        sta     copy_destination+2
        lda     #$4F
        sta     copy_source+1
        lda     #$90
        sta     copy_source+2
copy_loop:
copy_source:
        lda     $FFFF
copy_destination:
        sta     $FFFF
        inc     copy_source+1
        bne     source_ready
        inc     copy_source+2
source_ready:
        inc     copy_destination+1
        bne     destination_ready
        inc     copy_destination+2
destination_ready:
        lda     copy_source+1
        cmp     #$D7
        bne     copy_loop
        lda     copy_source+2
        cmp     #$90
        bne     copy_loop
