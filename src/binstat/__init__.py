# -*- coding: UTF-8 -*-
import numpy as np
import os
import warnings

from .features import *
from .features import __all__ as _features
from .model import *
from .model import __all__ as _model


__all__ = ["BinStat", "DEFAULT_MODEL", "MODELS", "THRESHOLD", "executable_format"] + _features + _model


# shipped models, named after the executable format they were trained on (e.g. models/elf.json for ELF)
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
MODELS = {os.path.splitext(f)[0]: os.path.join(MODELS_DIR, f) for f in sorted(os.listdir(MODELS_DIR))
          if f.endswith(".json")}
# model used unless another one is given, whatever the executable format
DEFAULT_MODEL = MODELS["pe"]
THRESHOLD = .5
# executable formats: (short name, article and full name), for the warnings about models of another format
FORMATS = {'elf': ("ELF", "an ELF executable"), 'macho': ("Mach-O", "a Mach-O executable"),
           'pe': ("PE", "a Portable Executable")}
MACHO_MAGICS = (b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe")


def executable_format(executable):
    """ Detect the format of the input executable from its magic bytes: "elf", "macho", "pe" or None (unknown). """
    with open(str(executable), "rb") as f:
        head = f.read(64)
        if head[:4] == b"\x7fELF":
            return "elf"
        # universal binaries share their magic with Java classes, whose version (>= 45) is where the number of
        #  architectures is
        if head[:4] in MACHO_MAGICS or head[:4] == b"\xca\xfe\xba\xbe" and 0 < int.from_bytes(head[4:8], "big") < 45:
            return "macho"
        if head[:2] == b"MZ" and len(head) == 64:
            f.seek(int.from_bytes(head[60:64], "little"))
            if f.read(4) == b"PE\0\0":
                return "pe"


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
        """ Configure the detector with a model (Model instance, path to a JSON model or name of a shipped model ;
             None for the default one, i.e. the PE model, or the ELF model for ELF executables) and the minimum ratio of
             packed blocks for an executable to be packed. """
        if not 0. <= threshold <= 1.:
            raise ValueError("threshold must be between 0 and 1")
        # without a given model, ELF executables get the ELF model (loaded on first use)
        self._default, self._elf_model = model is None, None
        if isinstance(model, Model):
            self.model, self._format = model, None
        else:
            path = str(model or DEFAULT_MODEL)
            path = path if os.path.isfile(path) else MODELS.get(path, path)
            self.model = Model.load(path)
            # a shipped model, whether by default, by name or by path, is only meant for the format it is named after
            self._format = {os.path.realpath(p): name for name, p in MODELS.items()}.get(os.path.realpath(path))
        self.threshold = threshold
        self.logger = logger

    def blocks(self, executable):
        """ Classify each block of the input executable (1 = packed, 0 = not packed). """
        model, model_fmt = self.model, self._format
        fmt = executable_format(executable) if model_fmt else None
        if self._default and fmt == "elf":
            if self._elf_model is None:
                self._elf_model = Model.load(MODELS["elf"])
            model, model_fmt = self._elf_model, "elf"
            if self.logger:
                self.logger.debug(f"{executable} is an ELF executable, using the ELF model (no model given)")
        X = file_features(str(executable), **model.features_kwargs)
        if len(X) > 0 and model_fmt and fmt != model_fmt:
            short, full = FORMATS.get(model_fmt, (model_fmt, f"a {model_fmt} executable"))
            msg = f"{executable} is not {full}, while the model was trained on {short} files"
            if self.logger:
                self.logger.warning(msg)
            else:
                warnings.warn(msg, stacklevel=2)
        return model.predict(X)

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
