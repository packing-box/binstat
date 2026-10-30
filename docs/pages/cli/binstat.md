# `binstat`: detect packing

`binstat` has three commands: `detect` applies the [method](../internals.md)
to one executable, `features` prints the measures of its blocks, and `train`
builds a model.

```console
$ binstat [-h] {detect,features,train} ...
```

The extra arguments are accepted by every command:

| Option | Description |
|---|---|
| `-b`, `--benchmark` | Print the elapsed time, in seconds, after the result. |
| `-v`, `--verbose` | Show debug information. |
| `-h`, `--help` | Show the help message and exit. |

## `detect`

```console
$ binstat detect [-h] [-b] [-v] [-m MODEL] [-r] [-t THRESHOLD] path
```

| Argument | Default | Description |
|---|---|---|
| `path` | | The executable to analyze. It must exist. |
| `-m`, `--model MODEL` | `elf` for ELF executables, otherwise `pe` (see [shipped models](../internals.md#shipped-models)) | Path to a JSON model made with `binstat train`, or name of a shipped model (`elf`, `pe`). A shipped model warns about files of another format (e.g. a PE file with `elf`). |
| `-r`, `--ratio` | | Print the ratio of packed blocks (0 to 1) instead of the decision. |
| `-t`, `--threshold T` | 0.5 | Report the file as packed when at least this ratio of its blocks is classified as packed. |

`detect` prints one of:

| Output | Meaning |
|---|---|
| `True` | The executable is packed. |
| `False` | The executable is not packed. |
| `?` | The file could not be analyzed, for instance because it is empty. An error message is logged before. |

```console
$ binstat detect upx_AccessEnum.exe -v
DEBUG:binstat:43/53 blocks recognized as packed (81.13%, threshold: 50.00%)
True
$ binstat detect AccessEnum.exe -r
0.10344827586206896
$ binstat detect empty.bin
ERROR:binstat:empty.bin has no block to analyze
?
```

With `-b`, the elapsed time is printed on a second line:

```console
$ binstat detect upx_AccessEnum.exe -b
True
0.1589635200216435
```

## `features`

```console
$ binstat features [-h] [-b] [-v] [--block-size BLOCK_SIZE] [--minkowski-order MINKOWSKI_ORDER]
                   [--ngram {1,2,3,4}] [--label {yes,no,?}] path
```

Prints one line per block, in the data format of C5.0 used in the paper: the
thirteen measures (in the order of the
[statistical module](../internals.md#statistical-module)), the label, the
block ID and the MD5 hash of the file.

| Argument | Default | Description |
|---|---|---|
| `path` | | The file to analyze. |
| `--block-size N` | 1024 | Size of the blocks, in bytes. |
| `--minkowski-order L` | 3 | Order (λ) of Minkowski's distance. |
| `--ngram {1,2,3,4}` | 1 | N-gram size: unigrams to four-grams. |
| `--label {yes,no,?}` | `?` | Label written on each line: `yes` for packed, `no` for not packed, `?` for unknown. |

```console
$ binstat features upx_AccessEnum.exe --label yes | sed -n 30p
0.006153,98.286241,0.029636,0.667969,0.015625,0.335294,0.760964,0.470518,7.490726,0.143848,0.045007,106.125987,0.333984,yes,BLOCK29,4b3100f06375038db79b375d7ae1de70
```

## `train`

```console
$ binstat train [-h] [-b] [-v] -n NOT_PACKED [NOT_PACKED ...] -o OUTPUT -p PACKED [PACKED ...]
                [--block-size BLOCK_SIZE] [--minkowski-order MINKOWSKI_ORDER] [--ngram {1,2,3,4}]
                [--balanced] [--boost BOOST] [--max-blocks MAX_BLOCKS] [--max-leaf-nodes MAX_LEAF_NODES]
                [--seed SEED]
```

Trains a model and saves it as JSON. It needs scikit-learn
(`pip install binstat[train]`). Every block of a packed executable is
labelled packed, and every block of a not packed executable not packed.

| Argument | Default | Description |
|---|---|---|
| `-p`, `--packed PATH ...` | | Packed executables, or folders holding them (walked recursively). Can be repeated. |
| `-n`, `--not-packed PATH ...` | | Not packed executables, or folders holding them. Can be repeated. |
| `-o`, `--output FILE` | | Path to the output JSON model. |
| `--block-size`, `--minkowski-order`, `--ngram` | 1024, 3, 1 | Parameters of the statistical module, as for `features`. They are stored in the model. |
| `--balanced` | | Weight the blocks so that both classes weigh the same. |
| `--boost N` | 30 | Number of boosting trials. |
| `--max-blocks N` | all | Maximum number of blocks taken at random from each executable. |
| `--max-leaf-nodes N` | unlimited | Maximum number of leaves of each tree. |
| `--seed N` | | Random seed, for reproducible models. |

```console
$ binstat train -p packed/ -n not-packed/ -o model.json --max-leaf-nodes 700 --seed 0
INFO:binstat:training on [...] blocks ([...] packed, [...] not packed)
INFO:binstat:model saved to model.json
$ binstat detect program.exe -m model.json
```

## Exit code

| Code | Meaning |
|---|---|
| `0` | The command ran, whatever the result (including `?`). |
| `1` | An unexpected error occurred, for instance an invalid model. |
| `2` | Invalid arguments. |

!!! note
    The exit code does not tell whether the file is packed. Parse the output,
    or use the [Python API](../api.md), for that.
