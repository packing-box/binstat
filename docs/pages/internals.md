# How it works

## Overview

```text
                 ┌──────────────────── statistical module ────────────────────┐   ┌─ classification ─┐
 program.exe ──▶ 1024-byte blocks ──▶ n-gram frequencies ──▶ 13 measures/block ──▶ boosted trees ──▶ packed / not packed per block
                                                                                                          │
                                                                    ratio of packed blocks ≥ threshold? ◀─┘
                                                                          │yes            │no
                                                                          ▼               ▼
                                                                         True           False
```

BinStat implements the method of Park, Ruiz and Montes,
[*BinStat - Tool for Recognition of Packed Executables*](https://doi.org/10.5769/J201101003)
(The International Journal of Forensic Computer Science, 2011). Packing
(compression or encryption) flattens the distribution of byte values, so
statistical measures of that distribution tell packed data from code and
regular data. The paper splits the tool into four modules:

1. the **statistical module** splits the executable into blocks and computes
   thirteen measures per block;
2. the **decision module** trains decision trees on the measures of the
   blocks of known packed and not packed executables (training phase);
3. the **classification module** classifies each block of an executable with
   these trees (production phase);
4. the **result parser** formats the result: here, the executable is packed
   when at least half of its blocks are (the paper's criterion; see
   `--threshold`).

## Statistical module

The executable is split into blocks of 1024 bytes; the last block may be
shorter. For each block, the frequency `X_f` of each n-gram value `f` is
computed, for unigrams (one byte, `0 ≤ f < 256`) up to four-grams (four
bytes, `0 ≤ f < 256⁴`). The n-grams overlap (a block of `N` bytes holds
`N - n + 1` n-grams) but do not cross block boundaries.

The thirteen measures, in this order (the columns of `binstat.FEATURES`), are
computed from these frequencies. Except Simpson's index and the entropy, they
compare the frequencies of **consecutive values** `X_f` and `X_f+1`, summed
over `0 ≤ f < M - 1`, with `M = 256ⁿ` the number of possible values:

| # | Measure | Formula |
|---|---|---|
| 1 | Simpson's index | `Σ k_f (k_f - 1) / (N (N - 1))`, with `k_f` the count of value `f` and `N` the number of n-grams |
| 2 | Canberra's distance | `Σ │X_f - X_f+1│ / (X_f + X_f+1)` |
| 3 | Minkowski's distance | `(Σ │X_f - X_f+1│^λ)^(1/λ)`, with `λ = 3` |
| 4 | Manhattan's distance | `Σ │X_f - X_f+1│` |
| 5 | Chebyshev's distance | `max │X_f - X_f+1│` |
| 6 | Bray-Curtis' distance | `Σ │X_f - X_f+1│ / Σ (X_f + X_f+1)` |
| 7 | Angular separation | `Σ X_f X_f+1 / √(Σ X_f² · Σ X_f+1²)` |
| 8 | Correlation coefficient | `Σ (X_f - m)(X_f+1 - m) / √(Σ (X_f - m)² · Σ (X_f+1 - m)²)`, with `m = 1/M` |
| 9 | Entropy | `- Σ X_f log₂ X_f` |
| 10 | Kullback-Leibler's divergence | `Σ X_f log₁₀(X_f / X_f+1)` |
| 11 | Jensen-Shannon's divergence | `½ Σ X_f log₁₀(X_f / A_f) + ½ Σ X_f+1 log₁₀(X_f+1 / A_f)`, with `A_f = (X_f + X_f+1) / 2` |
| 12 | Itakura-Saito's divergence | `Σ (X_f / X_f+1 - log₁₀(X_f / X_f+1) - 1)` |
| 13 | Total variation | `½ Σ │X_f - X_f+1│` |

As a block holds at most 1024 distinct n-grams, only the non-zero frequencies
are computed: bigrams to four-grams cost about as much as unigrams.

### Interpretation choices

The paper leaves a few points open. BinStat makes these choices:

- **Logarithms**: the paper writes "log" for the three divergences. With
  decimal logarithms, the measures of UPX-packed blocks match the sample line
  the paper gives for such a block (with natural logarithms, both the
  Kullback-Leibler and Jensen-Shannon divergences are about 2.3 times too
  high). The entropy is in bits, as the paper states.
- **Zero frequencies**: the terms where a ratio is undefined are skipped: pairs
  where both frequencies are zero for Canberra's distance, and pairs where
  either one is zero for the Kullback-Leibler and Itakura-Saito divergences.
- **Angular separation**: the paper prints the formula of Bray-Curtis'
  distance (a typo, also visible in the indices of the Itakura-Saito
  formula). BinStat uses the usual angular separation, which matches the
  paper's sample line.
- **Mean frequency** of the correlation coefficient: `m = 1/M`, the mean
  over all the `M` possible values.

## Decision and classification modules

The paper builds the trees with C5.0 and adopts **unigrams with a boosting of
30 trials**, which gave the lowest block error rate (8.6%). C5.0 is not
available as a Python package, so BinStat trains with scikit-learn's
**AdaBoost (SAMME) of entropy-based decision trees**, with 30 trials by
default.

Models are stored as plain **JSON**: the structure of each tree and its
weight in the vote, the parameters of the statistical module, and the
training parameters. Loading a model never runs code (unlike pickle), and
classification only needs numpy. A block is packed when the weighted vote of
the trees says so.

Like in the paper, every block of a packed executable is labelled packed for
training, and every block of a not packed executable not packed.

## Shipped models

BinStat ships one model per executable format, in its `models` folder, named
after the format (`binstat.MODELS` maps these names to their paths):
`pe.json` and `elf.json`.

When no model is given (`--model`), BinStat reads the magic bytes of each
executable:

- an **ELF** executable (`\x7fELF`) is analyzed with the ELF model, as a
  debug message says (shown with `-v`);
- **any other file** is analyzed with the PE model, the default one
  (`binstat.DEFAULT_MODEL`).

A given model is used for every file. As each shipped model was trained on
one format only, using it (by default, or with `--model pe` or
`--model elf`) on a file of another format gives a warning:

```console
$ binstat detect /bin/bash -v
DEBUG:binstat:/bin/bash is an ELF executable, using the ELF model (no model given)
DEBUG:binstat:508/1413 blocks recognized as packed (35.95%, threshold: 50.00%)
False
$ binstat detect /bin/bash --model pe
WARNING:binstat:/bin/bash is not a Portable Executable, while the model was trained on PE files
False
$ binstat detect program.exe --model elf
WARNING:binstat:program.exe is not an ELF executable, while the model was trained on ELF files
True
```

The last result shows why: the ELF model classifies 54% of the blocks of this
not packed PE file (`tests/hello.exe`) as packed, where the PE model
classifies 10%.

The format comes from the magic bytes: `\x7fELF` for ELF, and `MZ` followed
by `PE\0\0` at the offset given at 0x3c for PE (see `executable_format` in
the [Python API](api.md#executable_format)). Models that are not shipped
with BinStat never warn.

### PE model

The PE model is trained and evaluated with the protocol of the paper, by
`scripts/train-default-model.py` (see [Contributing](contributing.md)), on
the [packed PE dataset](https://github.com/packing-box/dataset-packed-pe),
whose packed samples are packed versions of its not packed ones:

- **Settings of the paper**: unigrams, blocks of 1024 bytes, `λ = 3`, 30
  boosting trials, all the blocks of each executable, no class weighting.
  The trees are limited to 700 leaves, close to the size of the tree of the
  paper (680).
- **Test set**: 22 not packed executables drawn at random (seed 0), with
  their versions packed by the training packers and by **Themida**, a packer
  unseen during training, like in the paper.
- **Training set**: the 410 other not packed executables, and their versions
  packed by **MEW, UPX, FSG, PECompact and MPRESS**, 5 of the 7 packers of the
  paper (CExe and XComp97 are not in the dataset, nor NakedPack and Morphine,
  the paper's other unseen packers). That is 228,132 blocks, 55% packed.

Results on the test set, with the criterion of the paper (packed when at
least 50% of the blocks are):

| Test set | Blocks misclassified (mean) | Blocks misclassified (max) | Files misclassified | Paper (files misclassified) |
|---|---|---|---|---|
| Not packed | 10.7% | 24.2% | 0/22 | 0/22 |
| MEW | 5.3% | 19.6% | 0/22 | 0/22 (MEW 1.1) |
| UPX | 8.9% | 18.9% | 0/22 | 0/22 |
| FSG | 10.2% | 58.8% | 2/22 | 0/22 |
| PECompact | 9.8% | 19.2% | 0/22 | 0/22 |
| MPRESS | 8.3% | 25.1% | 0/22 | 0/22 |
| Themida (unseen) | 5.5% | 9.3% | 0/22 | 0/22 |

Like in the paper, every not packed executable is recognized, with up to a
quarter of its blocks classified as packed (the paper reports 6.5% to
44.7%), and Themida is easily detected although it was not used for
training. The only misclassified executables are two FSG-packed ones, where
the paper has one CExe-packed executable.

### ELF model

The ELF model is trained with `binstat train` on the whole
[packed ELF dataset](https://github.com/packing-box/dataset-packed-elf): its
not packed executables, and their versions packed by **ezuri, gzexe,
midgetpack, pakkero, UPX and ward**. It uses the settings of the PE model
(unigrams, blocks of 1024 bytes, `λ = 3`, 30 boosting trials, trees of at
most 700 leaves, no class weighting), with seed 42. As no executable was
kept for testing, it has no evaluation like the PE model's.

## Limitations

- Only PE and ELF executables have a model of their own: unless another
  model is given, every file that is not ELF is analyzed with the PE model
  (hence the warning above). The method does not parse the executable, so it accepts
  any file, but its results are only reliable with a model trained on the
  same format (`--model elf`, or `binstat train`, see
  [Contributing](contributing.md#adding-a-model-for-another-format)).
- Any high-entropy content counts: a not packed executable with large
  compressed resources or overlay (installers, self-extracting archives,
  embedded images) can be reported as packed.
- Packers that keep most of the original executable as is, or that hide the
  packed data in low-entropy encodings, can be missed.
