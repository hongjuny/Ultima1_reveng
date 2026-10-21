// Export candidate code/data spans and direct zero-page operand references.
// Ghidra auto-analysis can mistake inline bytes for code; these are leads only.
// @category UltimaI
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import java.io.FileWriter;
import java.io.PrintWriter;

public class ExportUltimaMemory extends GhidraScript {
    private String kind(CodeUnit unit) {
        if (unit instanceof Instruction) return "instruction";
        if (unit instanceof Data && ((Data) unit).isDefined()) return "defined_data";
        return "undefined";
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) throw new IllegalArgumentException("expected output TSV path");
        String program = currentProgram.getName();
        try (PrintWriter out = new PrintWriter(new FileWriter(args[0]))) {
            out.println("kind\tprogram\tfrom\tto\toperand\tfunction\taccess");
            for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
                if (!block.isInitialized()) continue;
                Address spanStart = null;
                Address spanEnd = null;
                String spanKind = null;
                for (CodeUnit unit : currentProgram.getListing().getCodeUnits(
                        new AddressSet(block.getStart(), block.getEnd()), true)) {
                    String currentKind = kind(unit);
                    if (spanStart == null) {
                        spanStart = unit.getMinAddress();
                        spanKind = currentKind;
                    } else if (!spanKind.equals(currentKind)) {
                        out.printf("span\t%s\t%s\t%s\t%s\t\t%n",
                                   program, spanStart, spanEnd, spanKind);
                        spanStart = unit.getMinAddress();
                        spanKind = currentKind;
                    }
                    spanEnd = unit.getMaxAddress();
                    if (unit instanceof Data) {
                        Object value = ((Data) unit).getValue();
                        if (value instanceof Address) {
                            out.printf("pointer\t%s\t%s\t%s\tpointer\t\tdata%n",
                                       program, unit.getMinAddress(), value);
                        }
                    }
                    if (!(unit instanceof Instruction)) continue;
                    Instruction instruction = (Instruction) unit;
                    Function function = currentProgram.getFunctionManager().getFunctionContaining(
                            instruction.getAddress());
                    String owner = function == null ? "" : function.getName();
                    for (Reference ref : instruction.getReferencesFrom()) {
                        Address target = ref.getToAddress();
                        if (!target.isMemoryAddress() || target.getOffset() >= 0x100) continue;
                        boolean read = ref.getReferenceType().isRead();
                        boolean write = ref.getReferenceType().isWrite();
                        String access = read && write ? "readwrite" :
                                        read ? "read" : write ? "write" : "other";
                        out.printf("zp\t%s\t%s\t%s\t%s\t%s\t%s%n",
                                   program, instruction.getAddress(), target,
                                   instruction.getMnemonicString(), owner, access);
                    }
                }
                if (spanStart != null) {
                    out.printf("span\t%s\t%s\t%s\t%s\t\t%n",
                               program, spanStart, spanEnd, spanKind);
                }
            }
        }
        println(program + ": candidate code/data and zero-page references exported");
    }
}
