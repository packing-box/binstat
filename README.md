<p align="center"><img src="https://github.com/packing-box/binstat/raw/main/docs/pages/img/logo.png"></p>
<h1 align="center">BinStat <a href="https://twitter.com/intent/tweet?text=BinStat%20-%20Packing%20detector%20using%20statistics%20on%20byte%20n-grams%20and%20boosted%20decision%20trees.%0D%0Ahttps%3a%2f%2fgithub%2ecom%2fpacking-box%2fbinstat%0D%0A&hashtags=python,packer,packingdetection,machinelearning"><img src="https://img.shields.io/badge/Tweet--lightgrey?logo=twitter&style=social" alt="Tweet" height="20"/></a></h1>
<h3 align="center">Detect packed executables using statistics on the n-grams of their blocks and boosted decision trees.</h3>

[![PyPi](https://img.shields.io/pypi/v/binstat.svg)](https://pypi.python.org/pypi/binstat/)
[![Python Versions](https://img.shields.io/pypi/pyversions/binstat.svg)](https://pypi.python.org/pypi/binstat/)
[![Read The Docs](https://readthedocs.org/projects/binstat/badge/?version=latest)](https://binstat.readthedocs.io/en/latest/?badge=latest)
[![Build Status](https://github.com/packing-box/binstat/actions/workflows/python-package.yml/badge.svg)](https://github.com/packing-box/binstat/actions/workflows/python-package.yml)
[![Security](https://github.com/packing-box/binstat/actions/workflows/security.yml/badge.svg)](https://github.com/packing-box/binstat/actions/workflows/security.yml)
[![Coverage Status](https://raw.githubusercontent.com/packing-box/binstat/coverage-badge/docs/coverage.svg)](#)
[![License](https://img.shields.io/pypi/l/binstat.svg)](https://pypi.python.org/pypi/binstat/)


BinStat is an implementation of [this paper](https://doi.org/10.5769/J201101003) into a Python package with a console script to detect whether an executable is packed, using statistics on the n-grams of its blocks and boosted decision trees.

Models trained on PE (the default one) and ELF (used for ELF executables) files are included ; [scikit-learn](https://scikit-learn.org) is only needed for training your own models.

```session
$ pip install binstat
```

```session
$ binstat --help
[...]
usage examples:
- binstat detect program.exe
- binstat detect program.exe --threshold 0.6 --ratio
- binstat features program.exe --label yes
- binstat train -p packed/ -n not-packed/ -o model.json --max-blocks 100
```

## :bulb: Detection Mechanism

1. Split the executable into blocks of 1024 bytes
2. Compute the frequencies of the unigrams (bytes) of each block
3. Compute 13 statistical and information theory measures on these frequencies (Simpson's index, Canberra's distance, entropy, Kullback-Leibler's divergence, ...)
4. Classify each block as packed or not with boosted decision trees
5. If at least 50% of the blocks are packed, the input executable is packed ; otherwise, it is not


## :star: Related Projects

You may also like these:

- [Awesome Executable Packing](https://github.com/packing-box/awesome-executable-packing): A curated list of awesome resources related to executable packing.
- [Bintropy](https://github.com/packing-box/bintropy): Analysis tool for estimating the likelihood that a binary contains compressed or encrypted bytes (inspired from [this paper](https://ieeexplore.ieee.org/document/4140989)).
- [Dataset of packed ELF files](https://github.com/packing-box/dataset-packed-elf): Dataset of ELF samples packed with many different packers.
- [Dataset of packed PE files](https://github.com/packing-box/dataset-packed-pe): Dataset of PE samples packed with many different packers (fork of [this repository](https://github.com/chesvectain/PackingData)).
- [Docker Packing Box](https://github.com/packing-box/docker-packing-box): Docker image gathering packers and tools for making datasets of packed executables.
- [DSFF](https://github.com/packing-box/python-dsff): Library implementing the DataSet File Format (DSFF).
- [PEiD](https://github.com/packing-box/peid): Python implementation of the well-known Packed Executable iDentifier ([PEiD](https://www.aldeid.com/wiki/PEiD)).
- [PyPackerDetect](https://github.com/packing-box/pypackerdetect): Packing detection tool for PE files (fork of [this repository](https://github.com/cylance/PyPackerDetect)).
- [REMINDer](https://github.com/packing-box/reminder): Packing detector using a simple heuristic (inspired from [this paper](https://ieeexplore.ieee.org/document/5404211)).


<p align="center"><a href="#"><img src="https://img.shields.io/badge/Back%20to%20top--lightgrey?style=social" alt="Back to top" height="20"/></a></p>
