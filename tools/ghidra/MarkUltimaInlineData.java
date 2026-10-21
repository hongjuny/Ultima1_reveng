// Protect byte-matched inline arguments and short embedded tables from disassembly.
// These ranges were checked against reviewed ca65 fragments.
// @category UltimaI
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.ArrayDataType;
import ghidra.program.model.data.ByteDataType;

public class MarkUltimaInlineData extends GhidraScript {
    private static final String[][] RANGES = {
        {"U1.INTRO", "0B5A", "6", "mi_filename"},
        {"U1.INTRO", "0F2B", "12", "support_filename"},
        {"MI.U1", "890A", "4", "gen_filename"},
        {"MI.U1", "8926", "2", "other_filename_pointer"},
        {"GEN", "8A18", "4", "load_player_args"},
        {"GEN", "8F26", "6", "save_player_args"},
        {"OUT", "92DA", "6", "save_player_args"},
        {"SPA", "8FEE", "3", "up_display_args"},
        {"SPA", "8FF4", "8", "up_direction_deltas"},
        {"SPA", "9040", "3", "down_display_args"},
        {"SPA", "9046", "8", "down_direction_deltas"},
        {"SPA", "906E", "3", "right_display_args"},
        {"SPA", "9094", "3", "left_display_args"},
        {"STUPH", "1AB2", "18", "sound_effect_return_addresses"}
    };

    @Override
    public void run() throws Exception {
        String name = currentProgram.getName();
        int marked = 0;
        for (String[] row : RANGES) {
            if (!row[0].equals(name)) continue;
            Address address = toAddr(Integer.parseInt(row[1], 16));
            int length = Integer.parseInt(row[2]);
            createData(address, new ArrayDataType(ByteDataType.dataType, length, 1));
            createLabel(address, row[3], true);
            marked += length;
        }
        if (marked > 0) println(name + ": marked " + marked + " inline argument bytes");
    }
}
