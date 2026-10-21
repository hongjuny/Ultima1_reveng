; $9728-$972B: regenerate the map after ascending to a nonzero level.
.setcpu "6502"
.segment "CODE"

regenerate_level:
        jsr     $8C5D
        rts
