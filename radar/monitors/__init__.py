"""各購物平台的監控 monitor。

每個 monitor 都回傳統一的 ProductSnapshot 清單,交給 calendar_db 去重/合併/走狀態機。
"""

from .base import ProductSnapshot, Monitor  # noqa: F401
