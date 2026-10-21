; $98E3-$9935: reverse pursuit, try movement, recover 5 HP if blocked.
.setcpu "6502"
.segment "CODE"

        lda     $04
        bne     flip_x
        jsr     $15B9
        jsr     $9E45
flip_x:
        eor     #$80
        sta     $04
        lda     $05
        bne     flip_y
        jsr     $15B9
        jsr     $9E45
flip_y:
        eor     #$80
        sta     $05
        jsr     $9936
        bcc     done
        lda     $7EF5
        bmi     done
        clc
        lda     $7EF4
        adc     #$05
        sta     $7EF4
        lda     $7EF5
        adc     #$00
        sta     $7EF5
        cmp     #$01
        bne     threshold
        lda     $7EF4
        cmp     #$F4
threshold:
        bcc     done
        lda     #$01
        sta     $7EF2
        jsr     $9C93
        lda     #$02
        sta     $A476
        jsr     $9C64
done:
        rts
