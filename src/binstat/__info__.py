# -*- coding: UTF-8 -*-
"""BinStat package information.

"""
import os
from datetime import datetime

__y = str(datetime.now().year)
__s = "2026"

__author__    = "Alexandre D'Hondt"
__copyright__ = "© {} Alexandre D'Hondt".format([__y, __s + "-" + __y][__y != __s])
__license__   = "GPLv3 (https://www.gnu.org/licenses/gpl-3.0.fr.html)"
__reference__ = "https://doi.org/10.5769/J201101003"
__source__    = "https://github.com/packing-box/binstat"

with open(os.path.join(os.path.dirname(__file__), "VERSION.txt")) as f:
    __version__ = f.read().strip()

