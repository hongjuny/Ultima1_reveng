// Decode explicit overlapping entry points without changing Ghidra's main listing.
// Apple II code sometimes uses BIT absolute to skip an embedded LDA immediate.
// @category UltimaI
import ghidra.app.script.GhidraScript;
import ghidra.app.util.PseudoDisassembler;
import ghidra.program.model.listing.Instruction;
import java.io.FileWriter;
import java.io.PrintWriter;

public class ExportUltimaAlternateEntries extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        PseudoDisassembler decoder = new PseudoDisassembler(currentProgram);
        try (PrintWriter out = new PrintWriter(new FileWriter(args[0]))) {
            out.println("program\taddress\tend\tbytes\tmnemonic\toperands\tflow_type\tflows\tfallthrough\tfunction");
            for (int index = 1; index < args.length; index++) {
                Instruction instruction = decoder.disassemble(toAddr(Long.parseLong(args[index], 16)));
                StringBuilder bytes = new StringBuilder();
                for (byte value : instruction.getBytes()) bytes.append(String.format("%02X", value & 255));
                StringBuilder operands = new StringBuilder();
                for (int operand = 0; operand < instruction.getNumOperands(); operand++) {
                    if (operand != 0) operands.append(',');
                    operands.append(instruction.getDefaultOperandRepresentation(operand));
                }
                out.printf("%s\t%s\t%s\t%s\t%s\t%s\t%s\t\t%s\talternate_entry%n",
                           currentProgram.getName(), instruction.getMinAddress(), instruction.getMaxAddress(),
                           bytes, instruction.getMnemonicString(), operands, instruction.getFlowType(),
                           instruction.getFallThrough() == null ? "" : instruction.getFallThrough());
            }
        }
    }
}
