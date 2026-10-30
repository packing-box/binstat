# -*- coding: UTF-8 -*-
import hashlib
import logging
from argparse import ArgumentParser, RawTextHelpFormatter
from ast import literal_eval
from os.path import exists
from time import perf_counter

from .__info__ import __author__, __copyright__, __license__, __reference__, __source__, __version__
from .__init__ import BinStat, BLOCK_SIZE, MINKOWSKI_ORDER, MODELS, NGRAMS, THRESHOLD, file_features


def valid_file(path):
    if not exists(path):
        raise ValueError("input file does not exist")
    return path


class Positive:
    def __init__(self, *types, maximum=None, zero=True):
        self._types, self._max, self._zero = types, maximum, zero

    def __call__(self, string):
        try:
            n = literal_eval(string)
        except (SyntaxError, ValueError):
            raise ValueError(string)
        if not isinstance(n, self._types) or n < 0. or not self._zero and n == 0 or \
           self._max is not None and n > self._max:
            raise ValueError(string)
        return self._types[0](n)

    def __repr__(self):
        return "positive %s" % "|".join(map(lambda x: x.__name__, self._types))


def _features_args(parser):
    parser.add_argument("--block-size", type=Positive(int, zero=False), default=BLOCK_SIZE,
                        help="size of the blocks, in bytes (default: %d)" % BLOCK_SIZE)
    parser.add_argument("--minkowski-order", type=Positive(float, int, zero=False), default=MINKOWSKI_ORDER,
                        help="order (lambda) of Minkowski's distance (default: %d)" % MINKOWSKI_ORDER)
    parser.add_argument("--ngram", type=int, choices=NGRAMS, default=1, help="n-gram size (default: 1)")


def _detect(args):
    r = BinStat(args.model, args.threshold, args.logger)
    return r.ratio(args.path) if args.ratio else r.detect(args.path)


def _features(args):
    with open(args.path, "rb") as f:
        md5 = hashlib.md5(f.read()).hexdigest()
    kw = {k: getattr(args, k) for k in ["block_size", "minkowski_order", "ngram"]}
    # same format as the C5.0 data file of the paper: the measures, the label, the block ID and the MD5 of the file
    return "\n".join(",".join(["%f" % v for v in row] + [args.label, f"BLOCK{i}", md5])
                     for i, row in enumerate(file_features(args.path, **kw)))


def _train(args):
    kw = {k: getattr(args, k) for k in ["balanced", "block_size", "boost", "max_blocks", "max_leaf_nodes",
                                        "minkowski_order", "ngram", "seed"]}
    BinStat.train(args.packed, args.not_packed, logger=args.logger, **kw).model.save(args.output)
    args.logger.info(f"model saved to {args.output}")


def main():
    """ Tool's main function """
    descr = "BinStat {}\n\nAuthor   : {}\nCopyright: {}\nLicense  : {}\nReference: {}\nSource   : {}\n" \
            "\nThis tool computes statistics on the n-grams of each block of an executable and classifies the blocks" \
            " with boosted decision trees to determine if the executable is packed or not.\n\n"
    descr = descr.format(__version__, __author__, __copyright__, __license__, __reference__, __source__)
    examples = "usage examples:\n- " + "\n- ".join([
        "binstat detect program.exe",
        "binstat detect program.exe --threshold 0.6 --ratio",
        "binstat detect program --model elf",
        "binstat features program.exe --label yes",
        "binstat train -p packed/ -n not-packed/ -o model.json --max-blocks 100",
    ])
    parser = ArgumentParser(description=descr, epilog=examples, formatter_class=RawTextHelpFormatter)
    # extra arguments are accepted after each command
    common = ArgumentParser(add_help=False)
    extra = common.add_argument_group("extra arguments")
    extra.add_argument("-b", "--benchmark", action="store_true",
                       help="enable benchmarking, output in seconds (default: False)")
    extra.add_argument("-v", "--verbose", action="store_true", help="display debug information (default: False)")
    sparsers = parser.add_subparsers(dest="command", required=True, help="command to be executed")
    cmd = lambda name, help: sparsers.add_parser(name, help=help, description=help, parents=[common])
    detect = cmd("detect", "detect whether an executable is packed")
    detect.add_argument("path", type=valid_file, help="path to the executable file")
    detect.add_argument("-m", "--model", help="path to a JSON model, or name of a shipped model (%s) (default: elf for ELF "
                        "executables, otherwise pe ; a shipped model warns about files of another format)" %
                        ", ".join(MODELS))
    detect.add_argument("-r", "--ratio", action="store_true",
                        help="output the ratio of packed blocks instead of the decision")
    detect.add_argument("-t", "--threshold", type=Positive(float, int, maximum=1), default=THRESHOLD,
                        help="minimum ratio of packed blocks for the executable to be packed (default: %.1f)" %
                             THRESHOLD)
    features = cmd("features", "compute the measures of each block (in C5.0 data format)")
    features.add_argument("path", type=valid_file, help="path to the executable file")
    _features_args(features)
    features.add_argument("--label", choices=["yes", "no", "?"], default="?",
                          help="label of the blocks, 'yes' meaning packed (default: ?, i.e. unknown)")
    train = cmd("train", "train a model on packed and not packed executables")
    train.add_argument("-n", "--not-packed", action="extend", nargs="+", required=True,
                       help="not packed executables or folders holding them")
    train.add_argument("-o", "--output", required=True, help="path to the output JSON model")
    train.add_argument("-p", "--packed", action="extend", nargs="+", required=True,
                       help="packed executables or folders holding them")
    _features_args(train)
    train.add_argument("--balanced", action="store_true",
                       help="weight the blocks so that packed and not packed blocks weigh the same (default: False)")
    train.add_argument("--boost", type=Positive(int, zero=False), default=30,
                       help="number of boosting trials (default: 30)")
    train.add_argument("--max-blocks", type=Positive(int, zero=False),
                       help="maximum number of blocks taken at random from each executable (default: all)")
    train.add_argument("--max-leaf-nodes", type=Positive(int, zero=False),
                       help="maximum number of leaves of each tree (default: unlimited)")
    train.add_argument("--seed", type=int, help="random seed, for reproducible models")
    args = parser.parse_args()
    logging.basicConfig()
    args.logger = logging.getLogger("binstat")
    args.logger.setLevel([logging.INFO, logging.DEBUG][args.verbose])
    code = 0
    # execute the tool
    if args.benchmark:
        t1 = perf_counter()
    try:
        r = {'detect': _detect, 'features': _features, 'train': _train}[args.command](args)
        dt = str(perf_counter() - t1) if args.benchmark else ""
        if r is not None:
            print(str(r))
        if dt != "":
            print(dt)
    except Exception as e:
        args.logger.exception(e)
        code = 1
    return code
