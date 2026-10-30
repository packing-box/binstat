# -*- coding: UTF-8 -*-
"""Decision and classification modules of BinStat: boosted decision trees classifying blocks as packed or not.

The paper builds the trees with C5.0 (boosting of 30 trials). C5.0 is not available as a Python package, so training
 relies on scikit-learn's AdaBoost (SAMME) of entropy-based decision trees, which is the closest equivalent. Trained
 models are stored as plain JSON (no pickle), and classification only needs numpy.
"""
import json
import numpy as np

from .features import BLOCK_SIZE, FEATURES, MINKOWSKI_ORDER


__all__ = ["Model", "train"]


class Model:
    """ Boosted decision trees classifying blocks from their thirteen measures (1 = packed, 0 = not packed). """
    def __init__(self, trees, weights, ngram=1, block_size=BLOCK_SIZE, minkowski_order=MINKOWSKI_ORDER, **info):
        if len(trees) == 0 or len(trees) != len(weights):
            raise ValueError("a model needs as many weights as trees, and at least one tree")
        self.trees = [{k: np.asarray(t[k]) for k in ["left", "right", "feature", "threshold", "label"]} for t in trees]
        self.weights = np.asarray(weights, dtype="float64")
        self.ngram, self.block_size, self.minkowski_order = ngram, block_size, minkowski_order
        self.info = info

    @property
    def features_kwargs(self):
        """ Parameters of the statistical module the model was trained with. """
        return {'ngram': self.ngram, 'block_size': self.block_size, 'minkowski_order': self.minkowski_order}

    def predict(self, X):
        """ Classify blocks from their measures (array of shape (number of blocks, 13)). """
        X = np.asarray(X, dtype="float64").reshape(-1, len(FEATURES))
        # like scikit-learn, compare in single precision, as the thresholds were chosen between float32 values
        X = X.astype("float32")
        votes = np.zeros(len(X))
        for tree, w in zip(self.trees, self.weights):
            # weighted vote of each tree: +w for packed, -w for not packed
            votes += w * np.where(self._tree_predict(tree, X) == 1, 1., -1.)
        return (votes > 0).astype("int64")

    @staticmethod
    def _tree_predict(tree, X):
        node, rows = np.zeros(len(X), dtype="int64"), np.arange(len(X))
        while True:
            inner = tree['left'][node] >= 0
            if not inner.any():
                return tree['label'][node]
            n, r = node[inner], rows[inner]
            go_left = X[r, tree['feature'][n]] <= tree['threshold'][n]
            node[inner] = np.where(go_left, tree['left'][n], tree['right'][n])

    def to_dict(self):
        return {'format': "binstat-model", 'version': 1, 'features': FEATURES, **self.features_kwargs,
                'info': self.info, 'weights': self.weights.tolist(),
                'trees': [{k: v.tolist() for k, v in t.items()} for t in self.trees]}

    @classmethod
    def from_dict(cls, d):
        if d.get('format') != "binstat-model" or d.get('version') != 1:
            raise ValueError("not a BinStat model")
        if d.get('features') != FEATURES:
            raise ValueError("the model uses different features")
        return cls(d['trees'], d['weights'], d['ngram'], d['block_size'], d['minkowski_order'], **d.get('info', {}))

    @classmethod
    def load(cls, path):
        with open(path) as f:
            return cls.from_dict(json.load(f))

    def save(self, path):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, separators=(",", ":"))


def train(X, y, boost=30, max_leaf_nodes=None, min_samples_leaf=1, seed=None, sample_weight=None, balanced=False,
          **features_kwargs):
    """ Train boosted decision trees on block measures.

    :param X:                array of shape (number of blocks, 13)
    :param y:                block labels (1 = packed, 0 = not packed)
    :param boost:            number of boosting trials (the paper adopts 30)
    :param max_leaf_nodes:   maximum number of leaves of each tree (None for unlimited)
    :param min_samples_leaf: minimum number of blocks in a leaf
    :param seed:             random seed, for reproducible models
    :param sample_weight:    optional initial weight of each block
    :param balanced:         whether sample_weight balances the classes (only stored in the model information)
    :param features_kwargs:  parameters of the statistical module, stored in the model (ngram, block_size, ...)
    :return:                 Model instance
    """
    try:
        from sklearn.ensemble import AdaBoostClassifier
        from sklearn.tree import DecisionTreeClassifier
    except ImportError:  # pragma: no cover
        raise ImportError("training requires scikit-learn ; install it with: pip install binstat[train]")
    y = np.asarray(y)
    if set(np.unique(y)) != {0, 1}:
        raise ValueError("training needs both packed (1) and not packed (0) blocks")
    tree = DecisionTreeClassifier(criterion="entropy", max_leaf_nodes=max_leaf_nodes,
                                  min_samples_leaf=min_samples_leaf, random_state=seed)
    clf = AdaBoostClassifier(tree, n_estimators=boost, random_state=seed)
    clf.fit(np.asarray(X, dtype="float64"), y, sample_weight=sample_weight)
    trees = []
    for est in clf.estimators_:
        t = est.tree_
        trees.append({'left': t.children_left, 'right': t.children_right, 'feature': t.feature,
                      'threshold': t.threshold, 'label': est.classes_[t.value[:, 0, :].argmax(axis=1)]})
    # boosting may stop early when a tree is perfect ; only keep the trees that were actually fitted
    weights = clf.estimator_weights_[:len(trees)]
    return Model(trees, weights, boost=boost, balanced=balanced, max_leaf_nodes=max_leaf_nodes,
                 min_samples_leaf=min_samples_leaf, seed=seed, **features_kwargs)
