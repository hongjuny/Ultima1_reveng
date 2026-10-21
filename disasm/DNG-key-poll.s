; Dungeon bounded key read at $8DDA-$8DE5. The STUPH $15C2 stub
; polls at most $80 times; the final accumulator value is copied to X.
.setcpu "6502"
.segment "CODE"

poll_key:
        ldx     #$80
again:  jsr     $15C2
        bne     done
        dex
        bne     again
done:   tax
        rts
