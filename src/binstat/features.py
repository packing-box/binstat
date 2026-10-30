# -*- coding: UTF-8 -*-
"""Statistical module of BinStat: the thirteen block measures of Park et al.

Each block of the input is described by the frequencies X_f of its n-gram values f (0 <= f < M, with M = 256**n). Except
 Simpson's index and the entropy, the measures compare the frequencies of consecutive n-gram values, X_f and X_{f+1},
 for 0 <= f < M - 1. As a block holds at most 1024 distinct n-grams, only the non-zero frequencies are computed, so that
 bigrams to four-grams cost the same as unigrams.

The divergences (Kullback-Leibler, Jensen-Shannon and Itakura-Saito) use decimal logarithms: with these, the measures
 match the sample line given in the paper for a UPX-packed block, while the entropy is in bits as stated.
"""
import numpy as np


__all__ = ["BLOCK_SIZE", "FEATURES", "MINKOWSKI_ORDER", "NGRAMS", "block_features", "file_features"]


BLOCK_SIZE = 1024
FEATURES = ["simpson", "canberra", "minkowski", "manhattan", "chebyshev", "bray_curtis", "angular_separation",
            "correlation", "entropy", "kullback_leibler", "jensen_shannon", "itakura_saito", "total_variation"]
MINKOWSKI_ORDER = 3
NGRAMS = (1, 2, 3, 4)


def _div(a, b):
    """ Element-wise a / b, with 0 where b is 0. """
    out = np.zeros_like(a, dtype="float64")
    np.divide(a, b, out=out, where=b != 0)
    return out


def _histograms(data, ngram, block_size):
    """ Count the n-grams of each block.

    N-grams do not cross block boundaries ; the last block may be shorter than block_size, and is ignored when it is
     shorter than the n-gram.

    :return: (number of n-grams per block, sorted keys block * M + value of the n-grams, their counts)
    """
    a = np.frombuffer(data, dtype="uint8")
    n_blocks = (len(a) - ngram) // block_size + 1 if len(a) >= ngram else 0
    if n_blocks == 0:
        return np.zeros(0, dtype="int64"), np.zeros(0, dtype="int64"), np.zeros(0, dtype="int64")
    # value of the n-gram starting at each position (big-endian, so that f and f+1 differ in their last byte)
    start = np.arange(len(a) - ngram + 1, dtype="int64")
    values = np.zeros(len(start), dtype="int64")
    for j in range(ngram):
        values = (values << 8) | a[j:len(a) - ngram + 1 + j]
    # keep the n-grams lying entirely inside their block
    keep = start % block_size <= block_size - ngram
    block = start[keep] // block_size
    counts_per_block = np.bincount(block, minlength=n_blocks)
    if ngram == 1:
        # fast path: a dense histogram of 256 values per block
        dense = np.bincount(block * 256 + values[keep], minlength=n_blocks * 256)
        keys = np.flatnonzero(dense)
        return counts_per_block, keys, dense[keys]
    keys, counts = np.unique(block * 256 ** ngram + values[keep], return_counts=True)
    return counts_per_block, keys, counts


def _measures(n_per_block, keys, counts, ngram, minkowski_order=MINKOWSKI_ORDER):
    """ Compute the thirteen measures of each block from its sparse n-gram histogram. """
    m, nb = 256 ** ngram, len(n_per_block)
    bsum = lambda block, w: np.bincount(block, weights=w, minlength=nb)
    N = n_per_block.astype("float64")
    blk, val = keys // m, keys % m
    x = counts / N[blk]
    # pairs (X_f, X_{f+1}) where at least one of both is non-zero ; all the other pairs are (0, 0)
    f = np.union1d(keys[val <= m - 2], keys[val >= 1] - 1)
    pb = f // m
    i = np.searchsorted(keys, f)
    i[i == len(keys)] = 0
    xa = np.where(keys[i] == f, x[i], 0.)
    j = np.searchsorted(keys, f + 1)
    j[j == len(keys)] = 0
    xb = np.where(keys[j] == f + 1, x[j], 0.)
    d = np.abs(xa - xb)
    both = (xa > 0) & (xb > 0)
    r = np.where(both, xa / np.where(both, xb, 1.), 1.)
    mix = (xa + xb) / 2
    # correlation coefficient, with the mean frequency 1/M over the M values ; each (0, 0) pair contributes 1/M^2
    #  to each sum
    mean, zero_pairs = 1. / m, (m - 1) - bsum(pb, None)
    cov = bsum(pb, (xa - mean) * (xb - mean)) + zero_pairs * mean ** 2
    va = bsum(pb, (xa - mean) ** 2) + zero_pairs * mean ** 2
    vb = bsum(pb, (xb - mean) ** 2) + zero_pairs * mean ** 2
    chebyshev = np.zeros(nb)
    np.maximum.at(chebyshev, pb, d)
    manhattan = bsum(pb, d)
    return np.column_stack([
        # 1) Simpson's index
        _div(bsum(blk, counts * (counts - 1.)), N * (N - 1)),
        # 2) Canberra's distance (pairs (0, 0) are skipped)
        bsum(pb, _div(d, xa + xb)),
        # 3) Minkowski's distance of order lambda
        bsum(pb, d ** minkowski_order) ** (1. / minkowski_order),
        # 4) Manhattan's distance
        manhattan,
        # 5) Chebyshev's distance
        chebyshev,
        # 6) Bray-Curtis' distance
        _div(manhattan, bsum(pb, xa + xb)),
        # 7) Angular separation
        _div(bsum(pb, xa * xb), np.sqrt(bsum(pb, xa ** 2) * bsum(pb, xb ** 2))),
        # 8) Correlation coefficient
        _div(cov, np.sqrt(va * vb)),
        # 9) Entropy (bits)
        -bsum(blk, x * np.log2(x)),
        # 10) Kullback-Leibler's divergence (pairs where X_f or X_{f+1} is zero are skipped)
        bsum(pb, np.where(both, xa * np.log10(r), 0.)),
        # 11) Jensen-Shannon's divergence
        bsum(pb, (_xlogy(xa, mix) + _xlogy(xb, mix)) / 2),
        # 12) Itakura-Saito's divergence (pairs where X_f or X_{f+1} is zero are skipped)
        bsum(pb, np.where(both, r - np.log10(r) - 1, 0.)),
        # 13) Total variation
        manhattan / 2,
    ])


def _xlogy(x, y):
    """ x * log10(x / y), with 0 where x is 0. """
    out = np.zeros_like(x)
    nz = x > 0
    out[nz] = x[nz] * np.log10(x[nz] / y[nz])
    return out


def block_features(data, ngram=1, block_size=BLOCK_SIZE, minkowski_order=MINKOWSKI_ORDER):
    """ Compute the thirteen measures of each block of the input bytes.

    :param data:            bytes to analyze
    :param ngram:           n-gram size, from 1 (unigrams) to 4 (four-grams)
    :param block_size:      size of the blocks, in bytes
    :param minkowski_order: order (lambda) of Minkowski's distance
    :return:                array of shape (number of blocks, 13), with columns in the order of FEATURES
    """
    if ngram not in NGRAMS:
        raise ValueError(f"n-gram size must be one of {', '.join(map(str, NGRAMS))}")
    if block_size < ngram:
        raise ValueError("block size must be at least the n-gram size")
    n_per_block, keys, counts = _histograms(bytes(data), ngram, block_size)
    if len(n_per_block) == 0:
        return np.zeros((0, len(FEATURES)))
    return _measures(n_per_block, keys, counts, ngram, minkowski_order)


def file_features(path, **kwargs):
    """ Compute the thirteen measures of each block of a file (see block_features). """
    with open(path, "rb") as f:
        return block_features(f.read(), **kwargs)
