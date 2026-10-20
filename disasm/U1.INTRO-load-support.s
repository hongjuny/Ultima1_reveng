; Support-file request at $0F23-$0F40. Filename is inline data.
.setcpu "6502"
.segment "CODE"

first_intro_entry:
        lda     #$00
        sta     $03CE
retry_load:
        jsr     $B70C
        .byte   "MAKE.INDATA", $00
        bcs     retry_load
        lda     #$C7
        sta     $4E
        lda     #$55
        sta     $4F
