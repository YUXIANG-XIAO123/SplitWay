"""模型聚合。

Alembic 的 target_metadata 取自 app.db.Base.metadata，只有被导入过的模型才会进
metadata，因此新增模型必须在这里显式导入一次。
"""

from app.models.user import User

__all__ = ["User"]
