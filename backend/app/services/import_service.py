"""知识导入服务：封装导入工作流调用与任务进度追踪。"""

import asyncio
import uuid

from app.workflows.ingestion_graph import ingestion_graph


# 内存任务状态表：task_id -> {status, unit_ids, errors}
_TASKS: dict[str, dict] = {}


class ImportService:
    """知识导入业务逻辑。"""

    async def import_files(self, files: list[tuple[str, bytes]]) -> str:
        """接收上传文件，启动后台导入，返回 task_id。

        :param files: [(filename, content_bytes)]
        :return: task_id
        """
        task_id = uuid.uuid4().hex
        _TASKS[task_id] = {"status": "processing", "unit_ids": [], "errors": []}

        # 组装工作流初始状态
        init_state = {
            "task_id": task_id,
            "files": [{"filename": name, "raw": raw} for name, raw in files],
        }

        # 后台异步执行
        asyncio.create_task(self._run(task_id, init_state))
        return task_id

    async def _run(self, task_id: str, init_state: dict) -> None:
        """后台执行导入工作流并更新任务状态。"""
        try:
            result = await ingestion_graph.ainvoke(init_state)
            _TASKS[task_id]["status"] = "completed"
            _TASKS[task_id]["unit_ids"] = result.get("unit_ids", [])
            _TASKS[task_id]["errors"] = result.get("errors", [])
        except Exception as e:  # noqa: BLE001
            _TASKS[task_id]["status"] = "failed"
            _TASKS[task_id]["errors"] = [{"error": str(e)}]

    def get_status(self, task_id: str) -> dict | None:
        """查询导入任务进度。"""
        return _TASKS.get(task_id)


import_service = ImportService()
