// Define verified command tables as data before code auto-analysis.
// @category UltimaI
import ghidra.app.script.GhidraScript;
import ghidra.program.model.data.ArrayDataType;
import ghidra.program.model.data.ByteDataType;
import ghidra.program.model.data.PointerDataType;
import ghidra.program.model.address.Address;

public class MarkUltimaDispatch extends GhidraScript {
    private static final String[][] TABLES = {
        {"OUT", "9AAA"}, {"CAS", "8A5F"}, {"TWN", "8A56"},
        {"DNG", "8E14"}, {"SPA", "91D3"}, {"TM", "8EA8"}
    };

    @Override
    public void run() throws Exception {
        String name = currentProgram.getName();
        if (name.equals("MI.U1")) {
            Address keys = toAddr(0x7E53);
            createData(keys, new ArrayDataType(ByteDataType.dataType, 26, 1));
            createLabel(keys, "shared_command_keys", true);
            println("MI.U1: defined 26 command keys as data");
            return;
        }
        for (String[] row : TABLES) {
            if (!row[0].equals(name)) continue;
            if (currentProgram.getDefaultPointerSize() != 2) {
                throw new IllegalStateException("expected 16-bit 6502 pointers");
            }
            int base = Integer.parseInt(row[1], 16);
            for (int i = 0; i < 26; i++) {
                createData(toAddr(base + 2*i), new PointerDataType());
            }
            createLabel(toAddr(base), "command_handlers", true);
            println(name + ": defined 26 handler pointers at $" + row[1]);
            return;
        }
    }
}
