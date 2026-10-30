# Installation

## Requirements

- Python **3.10 or later**. CI runs on 3.10 to 3.13.
- [`numpy`](https://pypi.org/project/numpy/) (1.24 or later), which pip
  installs automatically.
- For training models only: [`scikit-learn`](https://pypi.org/project/scikit-learn/)
  (1.6 or later), installed with the `train` extra.

## From PyPI

The package is published on PyPI as **`binstat`**:

```console
$ pip install binstat
```

This installs the `binstat` Python package, its default model and the
`binstat` console script. Detection only needs numpy.

To also train your own models:

```console
$ pip install binstat[train]
```

## From source

```console
$ git clone https://github.com/dhondta/binstat
$ cd binstat
$ pip install .
```

For development, use an editable install with the training extra:

```console
$ pip install -e .[train]
```

## Checking the installation

```console
$ binstat --help
[...]
BinStat 1.0.0
[...]
```

```python
>>> from binstat.__info__ import __version__
>>> __version__
'1.0.0'
```
