import uuid
from sqlalchemy import select
from langgraph.types import Command

from app.db import AsyncSessionLocal
from .models import WorkflowSession
from .workflow import graph


class WorkflowService:
    def create_session(self) -> str:
        return str(uuid.uuid4())[:8]

    async def start(self, request: str) -> dict:
        thread_id = f"wf-{uuid.uuid4().hex[:6]}"
        config = {"configurable": {"thread_id": thread_id}}
        session_id = self.create_session()

        draft, status, usage = None, "running", {}

        for event in graph.stream({
            "session_id": session_id,
            "request": request, "template": None, "context": {}, "draft": None,
            "approved": False, "publish_status": None, "usage": {}, "error": None
        }, config=config):
            if "__interrupt__" in event:
                status = "paused"
                data = event["__interrupt__"][0].value
                draft, usage = data["draft"], data["usage"]
                break

        async with AsyncSessionLocal() as db:
            s = WorkflowSession(
                id=session_id,
                thread_id=thread_id,
                request=request,
                template=draft["metadata"]["type"] if draft else None,
                status=status,
                draft=draft,
                usage=usage
            )
            db.add(s)
            await db.commit()

        return {"session_id": session_id, "status": status, "draft": draft, "usage": usage}

    async def get_status(self, session_id: str) -> dict:
        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s = result.scalars().first()

            if not s:
                return None

            return {
                "session_id": session_id, "status": s.status, "draft": s.draft,
                "publish_status": s.publish_status, "approved": bool(s.approved),
                "usage": s.usage, "error": s.error
            }

    async def resume(self, session_id: str, action: str, content: str = None) -> dict:
        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s = result.scalars().first()
            if not s:
                return None

            config = {"configurable": {"thread_id": s.thread_id}}
            resume_cmd = {"action": action}
            if action == "edit" and content:
                resume_cmd["content"] = content

            result_graph = graph.invoke(Command(resume=resume_cmd), config=config)

            s.status = "completed"
            s.approved = 1 if result_graph.get("approved") else 0
            s.publish_status = result_graph.get("publish_status")
            s.draft = result_graph.get("draft")
            s.usage = result_graph.get("usage")
            s.error = result_graph.get("error")

            await db.commit()

            return {
                "session_id": session_id, "status": "completed", "draft": s.draft,
                "publish_status": s.publish_status, "approved": bool(s.approved),
                "usage": s.usage, "error": s.error
            }

    async def delete(self, session_id: str) -> bool:
        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s = result.scalars().first()

            if s:
                await db.delete(s)
                await db.commit()
                return True
            return False