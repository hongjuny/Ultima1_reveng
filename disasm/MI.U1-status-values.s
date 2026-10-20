; Numeric value rendering in the four-column status display, $837F-$83A8.
.setcpu "6502"
.segment "CODE"

status_values:
        lda     $7EC7
        ldx     $7EC6
        jsr     $8355
        lda     $7EE6
        ldx     $7EE5
        jsr     $8355
        lda     $7EE8
        ldx     $7EE7
        jsr     $8207
        jsr     $8086
        lda     $7ED5
        ldx     $7ED4
        jsr     $8207
        jsr     $1598
