"""讓 tests/ 能直接 import 專案根目錄的模組(config、calendar_db 等)。"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
