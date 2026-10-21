// Export Ghidra's candidate function and direct-call graph as TSV.
// It is an analysis aid; inline data and indirect dispatch need manual review.
// @category UltimaI
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;
import java.io.FileWriter;
import java.io.PrintWriter;

public class ExportUltimaCalls extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) throw new IllegalArgumentException("expected output TSV path");
        int functions = 0;
        int calls = 0;
        try (PrintWriter out = new PrintWriter(new FileWriter(args[0]))) {
            out.println("kind\tprogram\tfrom\tto\tname\tclassification");
            for (Function function : currentProgram.getFunctionManager().getFunctions(true)) {
                functions++;
                out.printf("function\t%s\t%s\t\t%s\tghidra_candidate%n",
                           currentProgram.getName(), function.getEntryPoint(), function.getName());
                for (Instruction instruction : currentProgram.getListing().getInstructions(function.getBody(), true)) {
                    if (!instruction.getFlowType().isCall()) continue;
                    for (Reference ref : instruction.getReferencesFrom()) {
                        if (!ref.getReferenceType().isCall()) continue;
                        calls++;
                        out.printf("call\t%s\t%s\t%s\t%s\tdirect%n",
                                   currentProgram.getName(), instruction.getAddress(),
                                   ref.getToAddress(), function.getName());
                    }
                }
            }
        }
        println(currentProgram.getName() + ": " + functions + " functions, " + calls + " direct call references");
    }
}
