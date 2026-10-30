# Contributing

Contributions are welcome, especially **models for other executable
formats** and **false positive or false
negative reports**.

## Reporting issues

Open an issue on [GitHub](https://github.com/packing-box/binstat/issues) and
include:

- the BinStat and numpy versions (`binstat --help` prints the former,
  `python -c "import numpy; print(numpy.__version__)"` the latter), and the
  scikit-learn version for training issues;
- the exact command and its output, ideally with `-v`;
- if possible, a link to (or the hash of) the sample.

## Security

Please do **not** report vulnerabilities in public issues. See the
[security policy](https://github.com/packing-box/binstat/blob/main/SECURITY.md):
report them privately through the repository's *Security* tab
(*Report a vulnerability*).

Dependencies are monitored by Dependabot and audited with
[pip-audit](https://github.com/pypa/pip-audit) by the `security` workflow
(`.github/workflows/security.yml`), on every push and pull request to `main`
and weekly.

## Training the PE model

The shipped models are in `src/binstat/models/`, one per executable format,
named after it (see [Shipped models](internals.md#shipped-models)). The PE
model, `pe.json`, is also the default one. It is trained with the protocol
of the paper on the
[packed PE dataset](https://github.com/packing-box/dataset-packed-pe), and
evaluated like in the paper, by:

```console
$ git clone https://github.com/packing-box/dataset-packed-pe
$ python3 scripts/train-default-model.py dataset-packed-pe
```

The script draws the test executables with a fixed seed, so it rebuilds the
same model. Keep any change of the PE model in line with the paper, and
evaluate it on executables that were not used for training.
[Docker Packing Box](https://github.com/packing-box/docker-packing-box) helps
with this.

## Adding a model for another format

`binstat train` the model on executables of that format, and save it in
`src/binstat/models/` under the name of the format (`macho.json` for
Mach-O): `--model macho` (or `BinStat("macho")`) then uses it. The PE model
stays the default one.

## Development setup

```console
$ git clone https://github.com/packing-box/binstat
$ cd binstat
$ pip install -e .[train]
$ pip install flake8 pytest pytest-cov
$ flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
$ pytest --cov=binstat
```

CI (`.github/workflows/python-package.yml`) installs the package on Python
3.10 to 3.13, runs this flake8 check and the tests. On `main`, it also
updates the coverage badge, kept alone on the `coverage-badge` branch.

## Releasing

The version is stored in `src/binstat/VERSION.txt`. On a push to `main`, CI
publishes the package to PyPI when this version is not on PyPI yet.

## Building this documentation

```console
$ pip install -r docs/requirements.txt
$ mkdocs serve -f docs/mkdocs.yml          # live preview at http://127.0.0.1:8000
$ mkdocs build --strict -f docs/mkdocs.yml # what Read the Docs runs
```

Read the Docs builds the site from `.readthedocs.yaml` at the root of the
repository.
