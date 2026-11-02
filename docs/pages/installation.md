# Installation

## Requirements

- Python **3.10 or later**. CI runs on 3.10 to 3.13.
- [`numpy`](https://pypi.org/project/numpy/) (1.24 or later; 2.1 or later on
  Python 3.13, 2.3.2 or later on Python 3.14), which pip installs
  automatically. Older numpy versions have no release for these Python
  versions and, built from source, can compute wrong measures.
- For training models only: [`scikit-learn`](https://pypi.org/project/scikit-learn/)
  (1.6 or later), installed with the `train` extra.

## From PyPI

The package is published on PyPI as **`binstat`**:

```console
$ pip install binstat
```

This installs the `binstat` Python package, its models and the
`binstat` console script. Detection only needs numpy.

To also train your own models:

```console
$ pip install binstat[train]
```

## From source

```console
$ git clone https://github.com/packing-box/binstat
$ cd binstat
$ pip install .
```

For development, use an editable install with the training extra:

```console
$ pip install -e .[train]
```

## Checking the installation

```console
$ binstat --version
BinStat 1.0.3
$ binstat --help
usage: binstat [-h] [--version] {detect,features,train} ...

BinStat 1.0.3

Author   : Alexandre D'Hondt
Copyright: © 2026 Alexandre D'Hondt
License  : GPLv3 (https://www.gnu.org/licenses/gpl-3.0.fr.html)
Reference: https://doi.org/10.5769/J201101003
Source   : https://github.com/packing-box/binstat

This tool computes statistics on the n-grams of each block of an executable and classifies the blocks with boosted decision trees to determine if the executable is packed or not.

positional arguments:
  {detect,features,train}
                        command to be executed
    detect              detect whether an executable is packed
    features            compute the measures of each block (in C5.0 data format)
    train               train a model on packed and not packed executables

options:
  -h, --help            show this help message and exit
  --version             show the version and exit

usage examples:
- binstat detect program.exe
- binstat detect program.exe --threshold 0.6 --ratio
- binstat detect program --model elf
- binstat features program.exe --label yes
- binstat train -p packed/ -n not-packed/ -o model.json --max-blocks 100
```

```python
>>> from binstat.__info__ import __version__
>>> __version__
'1.0.3'
```
