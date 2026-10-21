// Seed only observed entry points. Raw Apple II files also contain inline data.
// @category UltimaI
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;

public class SeedUltimaEntrypoints extends GhidraScript {
    private static final String[][] SEEDS = {
        {"U1.SYSTEM", "2000", "2088"},
        {"U1.INTRO", "0800", "0B50", "0F23", "1039"},
        {"MAKE.INDATA", "1E00", "1EFD"},
        {"MI.U1", "7000", "88F8", "82A2", "82E2", "836E", "8119"},
        {"STUPH", "1583", "15B0", "15C2", "15C5", "1D64", "1DF1"},
        {"GEN", "8956", "89FD", "8A10", "8AC0"},
        {"OUT", "8956", "8995", "89A1", "89CB", "8A6A", "9927", "9958"},
        {"CAS", "8956", "8A31", "89E6", "9BC0"},
        {"TWN", "8956", "8A28", "89E4"},
        {"DNG", "8956", "8DE6", "8D99", "9C02"},
        {"SPA", "8956", "8A53", "8A5F"},
        {"TM", "8956", "8E5E", "8E80"}
    };

    @Override
    public void run() throws Exception {
        String name = currentProgram.getName();
        for (String[] row : SEEDS) {
            if (!row[0].equals(name)) continue;
            for (int i = 1; i < row.length; i++) {
                Address address = toAddr(Long.parseLong(row[i], 16));
                if (!currentProgram.getMemory().contains(address)) continue;
                disassemble(address);
                if (currentProgram.getFunctionManager().getFunctionAt(address) == null) {
                    createFunction(address, "entry_" + row[i]);
                }
                println(name + " seeded $" + row[i]);
            }
            return;
        }
        println(name + ": no entry-point seed list");
    }
}
