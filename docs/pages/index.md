# BinStat

<p align="center"><img src="img/logo.png" alt="BinStat logo" width="200"></p>

**BinStat** detects whether an executable is packed using statistics on the
n-grams of its blocks and boosted decision trees. It implements the method of
Park, Ruiz and Montes in
[*BinStat - Tool for Recognition of Packed Executables*](https://doi.org/10.5769/J201101003)
as a Python package with a console script.

[![PyPi](https://img.shields.io/pypi/v/binstat.svg)](https://pypi.python.org/pypi/binstat/)
[![Python Versions](https://img.shields.io/pypi/pyversions/binstat.svg)](https://pypi.python.org/pypi/binstat/)
[![Build Status](https://github.com/packing-box/binstat/actions/workflows/python-package.yml/badge.svg)](https://github.com/packing-box/binstat/actions/workflows/python-package.yml)
[![Security](https://github.com/packing-box/binstat/actions/workflows/security.yml/badge.svg)](https://github.com/packing-box/binstat/actions/workflows/security.yml)
[![License](https://img.shields.io/pypi/l/binstat.svg)](https://pypi.python.org/pypi/binstat/)

## Features

- **The method of the paper** (see [How it works](internals.md)): thirteen
  statistical and information theory measures on each block of 1024 bytes,
  boosted decision trees classifying the blocks, and an executable is packed
  when at least half of its blocks are.
- **A default model** trained with the protocol of the paper, on PE files, with
  [results close to the paper's](internals.md#default-model).
- **Trainable**: build your own models, for instance for ELF files, with
  bigrams to four-grams.
- **Light**: detection only needs numpy; models are plain JSON.
- **A command-line tool**, [`binstat`](cli/binstat.md), and a
  [Python API](api.md).

## Quick start

```console
$ pip install binstat
$ binstat detect upx_AccessEnum.exe
True
$ binstat detect AccessEnum.exe
False
```

From Python:

```python
from binstat import BinStat

print(BinStat().detect("program.exe"))  # True, False or "?"
```

## Related projects

BinStat is part of the [packing-box](https://github.com/packing-box) ecosystem:

- [Awesome Executable Packing](https://github.com/packing-box/awesome-executable-packing): a curated list of resources about executable packing.
- [Bintropy](https://github.com/packing-box/bintropy): estimates how likely a binary is to contain compressed or encrypted bytes.
- [Dataset of packed ELF files](https://github.com/packing-box/dataset-packed-elf) and [Dataset of packed PE files](https://github.com/packing-box/dataset-packed-pe).
- [Docker Packing Box](https://github.com/packing-box/docker-packing-box): a Docker image of packers and tools for building datasets of packed executables.
- [DSFF](https://github.com/packing-box/python-dsff): the DataSet File Format library.
- [PEiD](https://github.com/packing-box/peid): a Python implementation of the Packed Executable iDentifier.
- [PyPackerDetect](https://github.com/packing-box/pypackerdetect): a packing detector for PE files using several heuristics and PEiD signatures.
- [REMINDer](https://github.com/packing-box/reminder): a packing detector using an entropy heuristic on the entry point section.

## License

BinStat is released under the
[GNU General Public License v3 or later](https://www.gnu.org/licenses/gpl-3.0.html).
