# -*- coding: UTF-8 -*-
import numpy as np
import os

from .features import *
from .features import __all__ as _features
from .model import *
from .model import __all__ as _model


__all__ = ["BinStat", "DEFAULT_MODEL", "THRESHOLD"] + _features + _model


DEFAULT_MODEL = os.path.join(os.path.dirname(__file__), "model.json")
THRESHOLD = .5


def _files(*paths):
    """ Yield the files from the input paths, walking folders recursively (sorted, for reproducibility). """
    for path in paths:
        path = str(path)
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                dirs.sort()
                for f in sorted(files):
                    yield os.path.join(root, f)
        else:
            yield path


class BinStat:
    def __init__(self, model=None, threshold=THRESHOLD, logger=None, **kwargs):
        """ Configure the detector with a model (Model instance or path to a JSON model ; None for the default one)
             and the minimum ratio of packed blocks for an executable to be packed. """
        if not 0. <= threshold <= 1.:
            raise ValueError("threshold must be between 0 and 1")
        self.model = model if isinstance(model, Model) else Model.load(model or DEFAULT_MODEL)
        self.threshold = threshold
        self.logger = logger

    def blocks(self, executable):
        """ Classify each block of the input executable (1 = packed, 0 = not packed). """
        return self.model.predict(file_features(str(executable), **self.model.features_kwargs))

    def detect(self, executable):
        """ Analyze the input executable file: it is packed when the ratio of its packed blocks reaches the
             threshold. """
        r = self.ratio(executable)
        return r if r == "?" else bool(r >= self.threshold)

    def ratio(self, executable):
        """ Compute the ratio of packed blocks of the input executable. """
        try:
            blocks = self.blocks(executable)
        except OSError as e:
            self._log(f"{executable}: {e.strerror or e}", OSError)
            return "?"
        if len(blocks) == 0:
            self._log(f"{executable} has no block to analyze", ValueError)
            return "?"
        r = float(blocks.mean())
        if self.logger:
            self.logger.debug(f"{blocks.sum()}/{len(blocks)} blocks recognized as packed ({r:.2%}, threshold: "
                              f"{self.threshold:.2%})")
        return r

    def _log(self, msg, exception, level="error"):
        """ Helper for either logging a message if a logger is defined or raising an exception. """
        if self.logger:
            getattr(self.logger, level)(msg)
        else:
            raise exception(msg)

    @classmethod
    def train(cls, packed, not_packed, ngram=1, block_size=BLOCK_SIZE, minkowski_order=MINKOWSKI_ORDER, boost=30,
              balanced=False, max_blocks=None, max_leaf_nodes=None, min_samples_leaf=1, seed=None, threshold=THRESHOLD,
              logger=None, **kwargs):
        """ Train a detector on packed and not packed executables, labelling all the blocks of an executable with its
             own label.

        :param packed:     list of packed executables or folders holding them
        :param not_packed: list of not packed executables or folders holding them
        :param balanced:   weight the blocks so that both classes weigh the same (packed blocks usually outnumber
                            the others)
        :param max_blocks: maximum number of blocks taken (at random) from each executable (None for all)
        :return:           BinStat instance (its model can be saved with .model.save(path))
        :raise ValueError: if a measure of an executable is not finite
        """
        fkw = {'ngram': ngram, 'block_size': block_size, 'minkowski_order': minkowski_order}
        rng, X, y = np.random.default_rng(seed), [], []
        for label, paths in [(1, packed), (0, not_packed)]:
            for path in _files(*paths):
                try:
                    F = file_features(path, **fkw)
                except OSError as e:
                    if logger:
                        logger.warning(f"{path}: {e.strerror or e}")
                    continue
                # fail early with the culprit rather than with scikit-learn's error on the whole training set
                bad = ~np.isfinite(F)
                if bad.any():
                    blocks, features = np.nonzero(bad)
                    raise ValueError(f"{path}: non-finite {', '.join(FEATURES[i] for i in sorted(set(features)))} "
                                     f"in {len(set(blocks))} block(s), starting with block {blocks.min()} (check "
                                     f"that numpy supports this Python version)")
                if max_blocks is not None and len(F) > max_blocks:
                    F = F[np.sort(rng.choice(len(F), max_blocks, replace=False))]
                X.append(F)
                y.append(np.full(len(F), label))
                if logger:
                    logger.debug(f"{path}: {len(F)} blocks ({['not packed', 'packed'][label]})")
        X, y = np.vstack(X or [np.zeros((0, len(FEATURES)))]), np.concatenate(y or [np.zeros(0, dtype="int64")])
        if logger:
            logger.info(f"training on {len(y)} blocks ({int(y.sum())} packed, {int(len(y) - y.sum())} not packed)")
        w = (len(y) / (2 * np.bincount(y, minlength=2)))[y] if balanced and len(set(y)) == 2 else None
        m = train(X, y, boost=boost, max_leaf_nodes=max_leaf_nodes, min_samples_leaf=min_samples_leaf, seed=seed,
                  sample_weight=w, balanced=balanced, **fkw)
        return cls(m, threshold, logger)
