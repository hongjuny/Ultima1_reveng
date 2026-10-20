; OUT resurrection HP/food fill at $8A3A-$8A5E.
.setcpu "6502"
.segment "CODE"

fill_health:
        inc     $7EC6
        jsr     $8A5F
        lda     $7EC6
        cmp     #$63
        bcc     fill_health
fill_food:
        inc     $7EE5
        jsr     $8A5F
        lda     $7EE5
        cmp     #$63
        bcc     fill_food
        jsr     $8414
        lda     #$0A
        jsr     $15CE
        jmp     $8995
