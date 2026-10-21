// Export the candidate 6502 instruction stream for address-preserving port work.
// This listing is private and still needs code/data boundary review.
// @category UltimaI
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.MemoryBlock;
import java.io.FileWriter;
import java.io.PrintWriter;

public class ExportUltimaInstructions extends GhidraScript {
    private String address(Address value) {
        return value == null ? "" : value.toString();
    }

    private String bytes(byte[] values) {
        StringBuilder result = new StringBuilder();
        for (byte value : values) result.append(String.format("%02X", value & 0xff));
        return result.toString();
    }

    private String operands(Instruction instruction) {
        StringBuilder result = new StringBuilder();
        for (int index = 0; index < instruction.getNumOperands(); index++) {
            if (index != 0) result.append(",");
            result.append(instruction.getDefaultOperandRepresentation(index));
        }
        return result.toString().replace('\t', ' ').replace('\n', ' ');
    }

    private String flows(Instruction instruction) {
        StringBuilder result = new StringBuilder();
        for (Address target : instruction.getFlows()) {
            if (result.length() != 0) result.append(',');
            result.append(target);
        }
        return result.toString();
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) throw new IllegalArgumentException("expected output TSV path");
        int count = 0;
        try (PrintWriter out = new PrintWriter(new FileWriter(args[0]))) {
            out.println("program\taddress\tend\tbytes\tmnemonic\toperands\tflow_type\tflows\tfallthrough\tfunction");
            for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
                if (!block.isInitialized()) continue;
                AddressSet range = new AddressSet(block.getStart(), block.getEnd());
                for (Instruction instruction : currentProgram.getListing().getInstructions(range, true)) {
                    Function owner = currentProgram.getFunctionManager()
                        .getFunctionContaining(instruction.getAddress());
                    out.printf("%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s%n",
                               currentProgram.getName(), instruction.getMinAddress(),
                               instruction.getMaxAddress(), bytes(instruction.getBytes()),
                               instruction.getMnemonicString(), operands(instruction),
                               instruction.getFlowType(), flows(instruction),
                               address(instruction.getFallThrough()),
                               owner == null ? "" : owner.getName());
                    count++;
                }
            }
        }
        println(currentProgram.getName() + ": " + count + " candidate instructions exported");
    }
}
