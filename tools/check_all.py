#!/usr/bin/env python3
"""Run the available local extraction, assembly, and data checks."""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CHECKS = (
    ("baseline", ["tools/baseline.py", "verify"]),
    ("disk extraction", ["tools/verify_disk.py"]),
    ("file sizes and addresses", ["tools/disassemble.py", "--check"]),
    ("reviewed assembly", ["tools/verify_disasm.py"]),
    ("TCMAPS records", ["tools/extract_data.py", "--check"]),
    ("intro support relocation", ["tools/verify_intro_support.py"]),
    ("intro-to-engine handoff", ["tools/verify_intro_to_engine.py"]),
    ("first gameplay overlay", ["tools/verify_engine_to_gen.py"]),
    ("GEN menu entry", ["tools/verify_gen_menu.py"]),
    ("GEN new-character choice", ["tools/verify_gen_new_character.py"]),
    ("GEN state initialization", ["tools/verify_gen_first_input.py"]),
    ("GEN first attribute increase", ["tools/verify_gen_attribute_increase.py"]),
    ("GEN attribute bounds and navigation", ["tools/verify_gen_attribute_controls.py"]),
    ("GEN attribute completion", ["tools/verify_gen_attribute_completion.py"]),
    ("GEN race A", ["tools/verify_gen_race_a.py"]),
    ("GEN sex A", ["tools/verify_gen_sex_a.py"]),
    ("GEN class A", ["tools/verify_gen_class_a.py"]),
    ("GEN name A", ["tools/verify_gen_name_a.py"]),
    ("GEN confirmation Y", ["tools/verify_gen_confirm_yes.py"]),
    ("GEN player save", ["tools/verify_gen_player_save.py"]),
    ("GEN after save", ["tools/verify_gen_after_save.py"]),
    ("GEN player reload", ["tools/verify_gen_load_player.py"]),
    ("OUT loader probe", ["tools/verify_out_loader_probe.py"]),
    ("OUT RAM lookup and fallback", ["tools/verify_out_ram_attempt.py"]),
    ("OUT disk read stall", ["tools/verify_out_disk_attempt.py"]),
    ("OUT preserved-head load", ["tools/verify_out_head_position.py"]),
    ("OUT entry", ["tools/verify_out_entry.py"]),
    ("OUT first input", ["tools/verify_out_first_input.py"]),
    ("OUT unknown P key", ["tools/verify_out_key_p.py"]),
    ("OUT Space dispatch", ["tools/verify_out_key_space.py"]),
    ("OUT Space immediate effect", ["tools/verify_out_space_effect.py"]),
    ("OUT return after Space", ["tools/verify_out_after_space.py"]),
    ("OUT four direction keys", ["tools/verify_out_directions.py"]),
    ("OUT terrain and CAS entry", ["tools/verify_out_terrain_entry.py"]),
    ("CAS first input", ["tools/verify_cas_first_input.py"]),
    ("CAS left-edge exit", ["tools/verify_cas_exit_left.py"]),
    ("CAS right movement", ["tools/verify_cas_step_right.py"]),
    ("CAS blocked movement", ["tools/verify_cas_blocked_down.py"]),
    ("CAS actor collision", ["tools/verify_cas_occupied_tile.py"]),
    ("CAS attack", ["tools/verify_cas_attack.py"]),
    ("CAS guard retaliation", ["tools/verify_cas_guard_retaliation.py"]),
    ("CAS controlled guard miss", ["tools/verify_cas_guard_miss.py"]),
    ("CAS controlled death and resurrection", ["tools/verify_cas_guard_death.py"]),
    ("controlled resurrection player record", ["tools/verify_resurrection_record.py"]),
    ("OUT-to-TWN route and first input", ["tools/verify_out_to_twn.py"]),
    ("TWN food-shop purchase boundary", ["tools/verify_twn_food_shop.py"]),
    ("OUT-to-DNG route and first input", ["tools/verify_out_to_dng.py"]),
    ("DNG first key dispatch and move", ["tools/verify_dng_first_keys.py"]),
    ("DNG directions and wall", ["tools/verify_dng_directions.py"]),
    ("DNG first map generation", ["tools/verify_dng_generation.py"]),
    ("DNG first monster turn", ["tools/verify_dng_monster_turn.py"]),
)


def main() -> int:
    for name, args in CHECKS:
        print(f"\n[{name}]", flush=True)
        result = subprocess.run([sys.executable, *args], cwd=ROOT)
        if result.returncode:
            print(f"FAILED {name} (exit {result.returncode})", file=sys.stderr)
            return result.returncode
    print("\nAll available local checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
