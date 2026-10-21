; Reviewed shared Ctrl-A / N option toggles at $8845-$886F.
; $8119 consumes zero-terminated inline display bytes after the call.
.setcpu "6502"
.segment "CODE"

control_a:
        lda     $1580
        eor     #$FF
        jsr     $15E0
        sta     $7E71
        bne     print_on
print_off:
        jsr     $8119
        .byte   " off", $00
        rts

control_n:
        lda     $1581
        eor     #$FF
        sta     $1581
        sta     $7E72
        beq     print_off
print_on:
        jsr     $8119
        .byte   " on", $00
        rts
