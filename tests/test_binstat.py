#!/usr/bin/python
# -*- coding: UTF-8 -*-
import json
import logging
import os
import sys
from contextlib import redirect_stdout
from io import StringIO
from random import Random
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import numpy as np
from binstat import *
from binstat.__main__ import main


HERE = os.path.dirname(os.path.abspath(__file__))
PE = os.path.join(HERE, "hello.exe")
LOGGER = logging.getLogger("test-binstat")
LOGGER.setLevel(logging.DEBUG)


def naive_features(block, ngram=1, minkowski_order=3):
    """ Straightforward (dense) implementation of the thirteen measures of the paper for a single block. """
    m = 256 ** ngram
    k = np.bincount([int.from_bytes(block[i:i+ngram], "big") for i in range(len(block) - ngram + 1)],
                    minlength=m).astype("float64")
    N = k.sum()
    x = k / N
    a, b = x[:-1], x[1:]
    d, s, both, mean = np.abs(a - b), a + b, (a > 0) & (b > 0), 1. / m
    mix = s / 2
    jsd = sum(u * np.log10(u / w) for u, w in zip(a, mix) if u > 0) + sum(v * np.log10(v / w) for v, w in zip(b, mix)
                                                                          if v > 0)
    return np.array([
        (k * (k - 1)).sum() / (N * (N - 1)),
        (d[s > 0] / s[s > 0]).sum(),
        (d ** minkowski_order).sum() ** (1 / minkowski_order),
        d.sum(),
        d.max(),
        d.sum() / s.sum(),
        (a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()),
        ((a - mean) * (b - mean)).sum() / np.sqrt(((a - mean) ** 2).sum() * ((b - mean) ** 2).sum()),
        -(x[x > 0] * np.log2(x[x > 0])).sum(),
        (a[both] * np.log10(a[both] / b[both])).sum(),
        jsd / 2,
        (a[both] / b[both] - np.log10(a[both] / b[both]) - 1).sum(),
        d.sum() / 2,
    ])


def training_data(seed=0, n=300):
    """ Make blocks of random bytes (packed) and of skewed bytes (not packed), with their labels. """
    rng = np.random.default_rng(seed)
    packed = bytes(rng.integers(0, 256, 1024 * n, dtype="uint8"))
    not_packed = bytes(rng.choice(256, 1024 * n, p=np.arange(256, 0, -1) ** 4 / (np.arange(256, 0, -1) ** 4).sum())
                       .astype("uint8"))
    X = np.vstack([block_features(packed), block_features(not_packed)])
    return X, np.array([1] * n + [0] * n), packed, not_packed


class TestFeatures(TestCase):
    def test_against_naive_implementation(self):
        data = Random(0).randbytes(1500) + bytes(range(40)) * 30 + open(PE, "rb").read()[:2000]
        for ngram in [1, 2]:
            F = block_features(data, ngram=ngram)
            self.assertEqual(F.shape, ((len(data) - ngram) // 1024 + 1, len(FEATURES)))
            for i, row in enumerate(F):
                np.testing.assert_allclose(row, naive_features(data[i*1024:(i+1)*1024], ngram), rtol=1e-9, atol=1e-12)

    def test_larger_ngrams(self):
        data = open(PE, "rb").read()[:5000]
        for ngram in [3, 4]:
            F = block_features(data, ngram=ngram)
            self.assertEqual(F.shape, (5, len(FEATURES)))
            self.assertTrue(np.isfinite(F).all())
            # four-grams of a block with no repeated four-gram ; at most 1021 distinct values for 1021 n-grams
            self.assertLessEqual(F[:, FEATURES.index("entropy")].max(), np.log2(1024 - ngram + 1) + 1e-9)

    def test_paper_sample(self):
        # random bytes: a high entropy and adjacent frequencies with no correlation, like the paper's packed block
        F = block_features(Random(1).randbytes(1024))[0]
        self.assertGreater(F[FEATURES.index("entropy")], 7.5)
        self.assertLess(abs(F[FEATURES.index("correlation")]), .2)
        self.assertAlmostEqual(F[FEATURES.index("total_variation")], F[FEATURES.index("manhattan")] / 2)

    def test_options_and_edge_cases(self):
        self.assertEqual(block_features(b"").shape, (0, len(FEATURES)))
        self.assertEqual(block_features(b"abc", ngram=4).shape, (0, len(FEATURES)))
        self.assertEqual(block_features(b"a" * 100, block_size=10).shape, (10, len(FEATURES)))
        # a constant block: a single n-gram value, hence a null entropy and Simpson's index of 1
        F = block_features(b"\x00" * 1024)[0]
        self.assertEqual(F[FEATURES.index("entropy")], 0.)
        self.assertEqual(F[FEATURES.index("simpson")], 1.)
        # a last block of a single byte has no Simpson's index
        self.assertEqual(block_features(b"\x00" * 1025)[1, 0], 0.)
        F2 = block_features(Random(2).randbytes(2048), minkowski_order=1)
        np.testing.assert_allclose(F2[:, FEATURES.index("minkowski")], F2[:, FEATURES.index("manhattan")])
        self.assertRaises(ValueError, block_features, b"test", ngram=5)
        self.assertRaises(ValueError, block_features, b"test", ngram=2, block_size=1)
        np.testing.assert_array_equal(file_features(PE), block_features(open(PE, "rb").read()))


class TestModel(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.X, cls.y, cls.packed, cls.not_packed = training_data()

    def test_train_and_predict(self):
        from sklearn.ensemble import AdaBoostClassifier
        from sklearn.tree import DecisionTreeClassifier
        m = train(self.X, self.y, boost=5, max_leaf_nodes=4, seed=0)
        np.testing.assert_array_equal(m.predict(self.X), self.y)
        # the pure numpy classification gives the same results as scikit-learn, on the training blocks and others
        X2 = np.vstack([self.X, training_data(1, 100)[0], np.random.default_rng(0).random((100, len(FEATURES)))])
        for leaves in [4, None]:
            tree = DecisionTreeClassifier(criterion="entropy", max_leaf_nodes=leaves, random_state=0)
            clf = AdaBoostClassifier(tree, n_estimators=10, random_state=0).fit(self.X, self.y)
            m = train(self.X, self.y, boost=10, max_leaf_nodes=leaves, seed=0)
            np.testing.assert_array_equal(m.predict(X2), clf.predict(X2))

    def test_save_and_load(self):
        m = train(self.X, self.y, boost=3, seed=0, ngram=2, block_size=512)
        with TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "model.json")
            m.save(path)
            m2 = Model.load(path)
            with open(path) as f:
                d = json.load(f)
        self.assertEqual(m2.features_kwargs, {'ngram': 2, 'block_size': 512, 'minkowski_order': 3})
        self.assertEqual(m2.info['boost'], 3)
        np.testing.assert_array_equal(m2.predict(self.X), m.predict(self.X))
        self.assertRaises(ValueError, Model.from_dict, {**d, 'format': "other"})
        self.assertRaises(ValueError, Model.from_dict, {**d, 'features': FEATURES[::-1]})
        self.assertRaises(ValueError, Model, [], [])

    def test_invalid_labels(self):
        self.assertRaises(ValueError, train, self.X, np.ones(len(self.y)))


class TestBinStat(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = TemporaryDirectory()
        cls.random = os.path.join(cls.tmp.name, "random.bin")
        with open(cls.random, "wb") as f:
            f.write(Random(0).randbytes(50 * 1024))
        cls.empty = os.path.join(cls.tmp.name, "empty.bin")
        open(cls.empty, "wb").close()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_default_model(self):
        b = BinStat()
        self.assertFalse(b.detect(PE))
        self.assertTrue(b.detect(self.random))
        self.assertEqual(b.ratio(self.random), 1.)
        self.assertEqual(len(b.blocks(PE)), (os.path.getsize(PE) - 1) // 1024 + 1)
        self.assertTrue(BinStat(threshold=0.).detect(PE))
        self.assertTrue(BinStat(DEFAULT_MODEL, logger=LOGGER).detect(self.random))

    def test_errors(self):
        self.assertRaises(ValueError, BinStat, threshold=1.5)
        self.assertRaises(ValueError, BinStat().detect, self.empty)
        self.assertRaises(OSError, BinStat().detect, os.path.join(self.tmp.name, "missing"))
        b = BinStat(logger=LOGGER)
        self.assertEqual(b.detect(self.empty), "?")
        self.assertEqual(b.detect(os.path.join(self.tmp.name, "missing")), "?")

    def test_train(self):
        X, y, packed, not_packed = training_data()
        with TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "packed", "sub"))
            os.makedirs(os.path.join(tmp, "not-packed"))
            for i in range(3):
                with open(os.path.join(tmp, "packed", "sub", f"p{i}"), "wb") as f:
                    f.write(packed[i * 100 * 1024:(i + 1) * 100 * 1024])
                with open(os.path.join(tmp, "not-packed", f"n{i}"), "wb") as f:
                    f.write(not_packed[i * 100 * 1024:(i + 1) * 100 * 1024])
            b = BinStat.train([os.path.join(tmp, "packed")], [os.path.join(tmp, "not-packed"),
                              os.path.join(tmp, "missing")], boost=3, max_blocks=20, seed=0, logger=LOGGER)
            self.assertTrue(b.detect(os.path.join(tmp, "packed", "sub", "p0")))
            self.assertFalse(b.detect(os.path.join(tmp, "not-packed", "n0")))
            self.assertRaises(ValueError, BinStat.train, [], [os.path.join(tmp, "not-packed")])


class TestCli(TestCase):
    def _main(self, *args):
        out = StringIO()
        with patch.object(sys, "argv", ["binstat", *args]), redirect_stdout(out):
            code = main()
        return code, out.getvalue().strip().splitlines()

    def test_detect(self):
        self.assertEqual(self._main("detect", PE), (0, ["False"]))
        code, out = self._main("detect", PE, "--ratio", "-t", "0.9", "-v", "-b")
        self.assertEqual(code, 0)
        self.assertLess(float(out[0]), .5)
        self.assertEqual(len(out), 2)
        self.assertEqual(self._main("detect", PE, "--model", PE), (1, []))
        with self.assertRaises(SystemExit):
            self._main("detect", PE, "-t", "2")

    def test_features(self):
        code, out = self._main("features", PE, "--label", "no", "--ngram", "2")
        self.assertEqual(code, 0)
        self.assertEqual(len(out), (os.path.getsize(PE) - 2) // 1024 + 1)
        fields = out[29].split(",")
        self.assertEqual(len(fields), len(FEATURES) + 3)
        self.assertEqual(fields[-3:-1], ["no", "BLOCK29"])

    def test_train(self):
        X, y, packed, not_packed = training_data(n=60)
        with TemporaryDirectory() as tmp:
            p, n, m = [os.path.join(tmp, f) for f in ["packed", "not-packed", "model.json"]]
            with open(p, "wb") as f:
                f.write(packed)
            with open(n, "wb") as f:
                f.write(not_packed)
            self.assertEqual(self._main("train", "-p", p, "-n", n, "-o", m, "--boost", "2", "--seed", "0"), (0, []))
            self.assertEqual(self._main("detect", p, "-m", m), (0, ["True"]))
