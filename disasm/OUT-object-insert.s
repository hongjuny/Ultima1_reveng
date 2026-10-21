; $9927-$9957: append one outdoor object to the saved player record.
; A is the unshifted tile type, X/Y are its 0..63 map coordinates.
.setcpu "6502"
.segment "CODE"

        cpx     #$40
        bcs     done
        cpy     #$40
        bcs     done
        stx     $6C
        ldx     $7EF6       ; active object count
        cpx     #$50        ; 80 slots; refuse a full array
        bcs     done
        asl     a
        sta     $7F97,x    ; object tile byte as written to map
        pha
        tya
        ora     $7E70       ; y plus world/continent bits
        sta     $7F47,x
        lda     $6C
        sta     $7EF7,x    ; x
        jsr     $98FA       ; locate map cell
        lda     ($72),y
        sta     $7FE7,x    ; tile hidden beneath object
        pla
        sta     ($72),y    ; draw object in map
        inc     $7EF6
        clc
done:
