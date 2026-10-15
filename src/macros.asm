// Long branches: the inverse branch over a jmp, for targets beyond -128..127 bytes.

.pseudocommand jeq target {
    bne !+
    jmp target
!:
}
.pseudocommand jne target {
    beq !+
    jmp target
!:
}
.pseudocommand jcc target {
    bcs !+
    jmp target
!:
}
.pseudocommand jcs target {
    bcc !+
    jmp target
!:
}
.pseudocommand jmi target {
    bpl !+
    jmp target
!:
}
.pseudocommand jpl target {
    bmi !+
    jmp target
!:
}
