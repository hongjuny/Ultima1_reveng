; GEN self-modifying player-record copy, $8A5B-$8A7E.
; Copies $6000-$61C9 to $7E6D-$8036, stopping as destination reaches $8037.
.setcpu "6502"
.segment "CODE"

copy_record:
        lda     $6000           ; source operand at $8A5C-$8A5D
        sta     $7E6D           ; destination operand at $8A5F-$8A60
        inc     $8A5C
        bne     source_advanced
        inc     $8A5D
source_advanced:
        inc     $8A5F
        bne     destination_advanced
        inc     $8A60
destination_advanced:
        lda     $8A5F
        eor     #$37
        bne     copy_record
        lda     $8A60
        eor     #$80
        bne     copy_record
