; Observed dungeon monster damage path at $9B05-$9B1F.
; Subtract the two-byte amount in $A4F2/$A4F3 from player HP.
.setcpu "6502"
.segment "CODE"

apply_damage:
        lda     $7EC6
        sec
        sbc     $A4F2
        sta     $7EC6
        lda     $7EC7
        sbc     $A4F3
        sta     $7EC7
        bcc     fatal
        jmp     $9A01
fatal:  jmp     $98DD
