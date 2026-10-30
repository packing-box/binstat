#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""Train the PE model of BinStat (its default one) with the protocol of the paper, and evaluate it like the paper does.

The paper trains on 456 not packed executables and their versions packed with 7 packers, then tests on 22 other
 executables and their packed versions, including a packer unseen during training (Themida). This script applies the
 same protocol to the packed PE dataset (https://github.com/packing-box/dataset-packed-pe), whose packed samples are
 named after their original (e.g. packed/UPX/upx_7z.exe for not-packed/7z.exe), with the 5 packers of the paper it holds.

usage: python3 scripts/train-default-model.py path/to/dataset-packed-pe [output.json]
"""
import logging
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from binstat import BinStat, DEFAULT_MODEL  # noqa: E402


TRAIN_PACKERS = ["MEW", "UPX", "FSG", "PECompact", "MPRESS"]  # CExe and XComp97 of the paper are not in the dataset
TEST_PACKERS = TRAIN_PACKERS + ["Themida"]                      # NakedPack and Morphine are not in the dataset
N_TEST, SEED = 22, 0


def main(dataset, output=DEFAULT_MODEL):
    logging.basicConfig(format="%(message)s")
    logger = logging.getLogger("binstat")
    logger.setLevel(logging.INFO)
    not_packed = sorted(os.listdir(os.path.join(dataset, "not-packed")))
    packed = {p: {f.split("_", 1)[1]: os.path.join(dataset, "packed", p, f)
                  for f in sorted(os.listdir(os.path.join(dataset, "packed", p))) if "_" in f} for p in TEST_PACKERS}
    # test executables: originals packed with every test packer, drawn at random
    candidates = sorted(set(not_packed).intersection(*packed.values()))
    test = sorted(np.random.default_rng(SEED).choice(candidates, N_TEST, replace=False))
    train_np = [os.path.join(dataset, "not-packed", f) for f in not_packed if f not in test]
    train_p = [path for p in TRAIN_PACKERS for orig, path in packed[p].items() if orig not in test]
    logger.info(f"training on {len(train_np)} not packed and {len(train_p)} packed executables")
    detector = BinStat.train(train_p, train_np, boost=30, max_leaf_nodes=700, seed=SEED, logger=logger)
    detector.model.save(output)
    logger.info(f"model saved to {output}\n")
    # evaluation, in the format of the tables of the paper
    print(f"{'Test set':12s} {'Blocks misclassified (mean / max)':>34s} {'Files misclassified':>20s}")
    for group in [None] + TEST_PACKERS:
        ratios = np.array([detector.ratio(os.path.join(dataset, "not-packed", f) if group is None else packed[group][f])
                           for f in test])
        # blocks recognized as packed for not packed executables (false positives), and the other way around
        errors = ratios if group is None else 1 - ratios
        wrong = ratios >= detector.threshold if group is None else ratios < detector.threshold
        print(f"{group or 'not packed':12s} {errors.mean():>25.3%} / {errors.max():.3%} {int(wrong.sum()):>13d}/{len(test)}")


if __name__ == "__main__":
    main(*sys.argv[1:])
