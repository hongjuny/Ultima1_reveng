#!/usr/bin/env python3
"""Verify the food-shop route, purchase, and exact Coin 4/5 boundary."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build" / "traces"
ROUTE = TRACE / "twn-to-food-shop"
MENU = TRACE / "twn-shop-menu" / "handoff.json"
PROMPT = TRACE / "twn-buy-prompt" / "handoff.json"
BUY = TRACE / "twn-buy-one" / "handoff.json"
BOUNDARIES = {coin: TRACE / f"twn-buy-boundary-{coin}" / "handoff.json"
              for coin in (4, 5)}


def checked_ram(item: dict) -> bytes:
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            "food-shop snapshot differs")
    return main_ram(path)


def main() -> int:
    paths = [TRACE / "twn-first-input" / "handoff.json"] + \
        [ROUTE / f"step-{step:02d}" / "handoff.json" for step in range(1, 11)] + \
        [MENU, PROMPT, BUY, *BOUNDARIES.values()]
    if not all(path.is_file() for path in paths):
        print("PENDING town food-shop route and purchase traces")
        return 0
    initial, *tail = [json.loads(path.read_text()) for path in paths]
    steps, menu, prompt, buy, poor, exact = tail[:10], *tail[10:]
    require(all(item["timeout"] is None for item in
                (initial, *steps, menu, prompt, buy, poor, exact)),
            "food-shop trace contains a stopped run")
    prior = initial
    for step, report in enumerate(steps, 1):
        position = [19, 17 - step] if step <= 6 else [19 + step - 6, 11]
        key = 0x0B if step <= 6 else 0x15
        require(report["source_snapshot"] == prior["snapshot"] and
                report["working_game_disk"] == initial["working_game_disk"] and
                report["input"]["key_ascii"] == key and
                report["position_after"] == position and
                [point["pc"] for point in report["checkpoints"]] ==
                ["0x8A26", "0x8A41", "0xA26F", "0x8A1E"],
                f"town food-shop route step {step} differs")
        prior = report
    at_shop = checked_ram(prior["snapshot"])
    overlay = (ROOT / "extracted" / "TWN").read_bytes()
    byte_at = lambda address: overlay[address - 0x8956]
    row_offsets = [byte_at(0xA96D + y) | byte_at(0xA97F + y) << 8
                   for y in range(18)]
    trade_pointer = byte_at(0x8A56 + 21 * 2) | byte_at(0x8A57 + 21 * 2) << 8
    shop_index = byte_at(0xA9AF + (0x66 - 0x64))
    buy_pointer = byte_at(0xA9DB + shop_index * 2) | \
        byte_at(0xA9DC + shop_index * 2) << 8
    require(row_offsets == list(range(0, 38 * 18, 38)) and
            trade_pointer == 0x9093 and shop_index == 1 and buy_pointer == 0x9257,
            "town map stride or shop dispatch tables differ")
    require(at_shop[0:2] == bytes((23, 11)) and
            at_shop[0xB400 + 11 * 38 + 23] == 0x66,
            "town food-shop tile differs")
    require(menu["source_snapshot"] == prior["snapshot"] and
            menu["shop_index"] == 1 and
            [point["pc"] for point in menu["checkpoints"]] ==
            ["0x8A26", "0x8A41", "0x9093", "0x90B5", "0x90F0", "0x8A1E"] and
            menu["before"] == menu["after"] ==
            {"coin": [100, 0], "food": [194, 0]},
            "trade menu routing differs")
    require(prompt["source_snapshot"] == menu["snapshot"] and
            prompt["price_per_pack"] == 5 and
            [point["pc"] for point in prompt["checkpoints"]] ==
            ["0x8A26", "0x911E", "0x9137", "0x9257", "0xA2F9"] and
            prompt["watched"] == {"coin": [100, 0], "food": [194, 0]} and
            checked_ram(prompt["snapshot"])[0x7ED2] == 15,
            "food price or Buy routing differs")
    require(buy["source_snapshot"] == prompt["snapshot"] and
            [point["pc"] for point in buy["checkpoints"]] ==
            ["0xA392", "0x92E0", "0x932F", "0x933E", "0x9362", "0x8A1E"] and
            buy["checkpoints"][2]["watched"]["cost_72"] == [5, 0] and
            buy["checkpoints"][2]["watched"]["quantity_aa69"] == [10, 0] and
            buy["before"]["coin"] == [100, 0] and
            buy["before"]["food"] == [194, 0] and
            buy["after"]["coin"] == [95, 0] and
            buy["after"]["food"] == [204, 0],
            "one-pack purchase arithmetic differs")
    for coin, report in ((4, poor), (5, exact)):
        require(report["source_snapshot"] == prompt["snapshot"] and
                report["controlled_change"] ==
                {"address": "0x7ED4", "before": 100, "after": coin} and
                report["working_game_disk"] == initial["working_game_disk"],
                f"Coin={coin} boundary ancestry differs")
        pre = checked_ram(report["intervention_snapshots"]["before"])
        post = checked_ram(report["intervention_snapshots"]["after"])
        require([(address, pre[address], post[address])
                 for address in range(0x10000) if pre[address] != post[address]] ==
                [(0x7ED4, 100, coin)] and pre[0x7ED5] == post[0x7ED5] == 0,
                f"Coin={coin} intervention changed more than one byte")
        branch, outcome = (("0x933B", "0x9236") if coin == 4 else
                           ("0x933E", "0x9362"))
        require([point["pc"] for point in report["checkpoints"]] ==
                ["0xA392", "0x92E0", "0x932F", branch, outcome, "0x8A1E"] and
                report["checkpoints"][2]["watched"]["cost_72"] == [5, 0],
                f"Coin={coin} comparison branch differs")
        expected = {"coin": [coin if coin == 4 else 0, 0],
                    "food": [194 if coin == 4 else 204, 0]}
        require(all(report["after"][name] == value for name, value in expected.items()),
                f"Coin={coin} purchase result differs")
        final = checked_ram(report["snapshot"])
        require(final[0x7ED4:0x7ED6] == bytes(expected["coin"]) and
                final[0x7EE5:0x7EE7] == bytes(expected["food"]),
                f"Coin={coin} final snapshot differs")
    print("TWN food shop: $66 tile, T→B, attribute $7ED2=15 gives 5 Coin per pack")
    print("one pack: Coin 100→95, food 194→204; Coin 4 fails, Coin 5 succeeds")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TWN food-shop verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
