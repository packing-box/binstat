# Python API

The `binstat` package exposes the detector, the statistical module and the
model:

```python
from binstat import BinStat, Model, block_features, file_features, train
```

---

## `BinStat`

```python
BinStat(model=None, threshold=0.5, logger=None, **kwargs)
```

Configures a detector. One instance can analyze many files.

| Parameter | Type | Description |
|---|---|---|
| `model` | `Model`, `str` or `None` | Model, path to a JSON model, or name of a [shipped model](internals.md#shipped-models) (a key of `binstat.MODELS`: `"elf"`, `"pe"`). `None` uses the ELF model for ELF executables (logging a debug message when a `logger` is set), and the default model (`binstat.DEFAULT_MODEL`, the PE model) for any other file. A shipped model, given in any way but as a `Model`, warns about files of another format. |
| `threshold` | `float` | Minimum ratio of packed blocks, from 0 to 1, for an executable to be packed. The paper uses 0.5. |
| `logger` | `logging.Logger` | Optional logger. When set, errors are logged and `detect` and `ratio` return `"?"`. Otherwise, errors raise exceptions. |
| `**kwargs` | | Ignored. It lets you pass `vars(args)` from an argument parser. |

**Raises** `ValueError` if `threshold` is not between 0 and 1.

### `detect`

```python
BinStat.detect(executable)
```

Analyzes one executable.

**Returns**:

- `True` if the ratio of its packed blocks reaches the threshold;
- `False` if it does not;
- `"?"` if it could not be analyzed (only when a `logger` is set).

**Raises**, when no `logger` is set:

- `OSError` if the file cannot be read;
- `ValueError` if the file has no block to analyze (an empty file, or one
  shorter than the n-gram).

### `ratio`

```python
BinStat.ratio(executable)
```

Returns the ratio of blocks classified as packed, from 0 to 1, or `"?"` like
`detect`.

### `blocks`

```python
BinStat.blocks(executable)
```

Returns the class of each block as a numpy array: `1` for packed, `0` for not
packed. Errors are raised, whatever the `logger`.

Without a given model, an ELF executable is classified with the ELF model.
With a shipped model, it warns about a file of another format than the
model's (and that has blocks to classify): through the `logger` when one is set,
otherwise with a `UserWarning`. `detect` and `ratio` rely on it, so they warn
the same way.

### `executable_format`

```python
executable_format(executable)
```

Detects the format of an executable from its magic bytes: `"elf"`,
`"macho"`, `"pe"`, or `None` when it is none of them (a DOS executable
without a PE header is `None`). Raises `OSError` if the file cannot be read.

### `train`

```python
BinStat.train(packed, not_packed, ngram=1, block_size=1024, minkowski_order=3, boost=30,
              max_blocks=None, max_leaf_nodes=None, min_samples_leaf=1, seed=None,
              threshold=0.5, logger=None, **kwargs)
```

Class method that trains a model and returns a detector using it. It needs
scikit-learn (`pip install binstat[train]`).

| Parameter | Description |
|---|---|
| `packed`, `not_packed` | Lists of executables, or folders holding them (walked recursively). Every block of an executable gets the label of the executable. |
| `ngram`, `block_size`, `minkowski_order` | Parameters of the [statistical module](internals.md#statistical-module), stored in the model. |
| `boost` | Number of boosting trials. |
| `max_blocks` | Maximum number of blocks taken at random from each executable. `None` takes them all. |
| `max_leaf_nodes`, `min_samples_leaf` | Size limits of each tree. |
| `seed` | Random seed, for reproducible models. |

Files that cannot be read are skipped (with a warning when a `logger` is
set). Save the model with `detector.model.save("model.json")`.

**Raises** `ValueError`, naming the file, the measures and the first block
concerned, when a measure of an executable is not finite (for instance with
a numpy build that does not support the running Python version).

---

## Statistical module

### `block_features`

```python
block_features(data, ngram=1, block_size=1024, minkowski_order=3)
```

Computes the thirteen measures of each block of `data` (bytes). Returns a
numpy array of shape `(number of blocks, 13)`, whose columns are in the order
of `binstat.FEATURES`:

```python
["simpson", "canberra", "minkowski", "manhattan", "chebyshev", "bray_curtis", "angular_separation",
 "correlation", "entropy", "kullback_leibler", "jensen_shannon", "itakura_saito", "total_variation"]
```

**Raises** `ValueError` if `ngram` is not 1 to 4 or `block_size` is smaller
than `ngram`.

### `file_features`

```python
file_features(path, **kwargs)
```

Same as `block_features`, for the content of a file.

---

## Models

### `train`

```python
train(X, y, boost=30, max_leaf_nodes=None, min_samples_leaf=1, seed=None,
      sample_weight=None, **features_kwargs)
```

Trains boosted decision trees on block measures `X` with labels `y` (`1` for
packed, `0` for not packed) and returns a `Model`. `features_kwargs`
(`ngram`, `block_size`, `minkowski_order`) are stored in the model, so that a
detector computes the measures the same way. It needs scikit-learn.

### `Model`

| Member | Description |
|---|---|
| `Model.load(path)` | Loads a JSON model. Raises `ValueError` if the file is not a BinStat model. |
| `model.save(path)` | Saves the model as JSON. |
| `model.predict(X)` | Classifies blocks from their measures. Returns an array of `1` (packed) and `0` (not packed). Only needs numpy. |
| `model.features_kwargs` | Parameters of the statistical module the model was trained with. |
| `model.info` | Training parameters (`boost`, `max_leaf_nodes`, `seed`, ...). |

## Example

```python
import logging
from binstat import BinStat

detector = BinStat(threshold=0.6, logger=logging.getLogger("binstat"))

# b.elf is analyzed with the ELF model, the others with the PE model, which warns about c.bin (not a PE)
for path in ["a.exe", "b.elf", "c.bin", "empty.bin"]:
    print(path, detector.detect(path), detector.ratio(path))
```

Training and using a model:

```python
from binstat import BinStat

detector = BinStat.train(["dataset/packed"], ["dataset/not-packed"], max_blocks=100, seed=0)
detector.model.save("model.json")
print(BinStat("model.json").detect("program.exe"))
```
