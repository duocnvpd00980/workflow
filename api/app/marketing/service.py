import uuid
from sqlalchemy import select
from langgraph.types import Command

from app.marketing.nodes import call_groq
from app.db import AsyncSessionLocal
from .models import WorkflowSession
from .workflow import graph


class WorkflowService:
    def create_session(self) -> str:
        return str(uuid.uuid4())[:8]

    async def start(self, request: str, auto_mode: bool = False) -> dict:
        thread_id = f"wf-{uuid.uuid4().hex[:6]}"
        config = {"configurable": {"thread_id": thread_id}}
        session_id = self.create_session()

        draft, status, usage = None, "running", {}

        # Nếu auto_mode: thêm flag để workflow skip review
        initial_state = {
            "session_id": session_id,
            "request": request,
            "template": None,
            "context": {},
            "draft": None,
            "approved": False,
            "publish_status": None,
            "usage": {},
            "error": None
        }

        async for event in graph.astream(initial_state, config=config):
            if "__interrupt__" in event:
                # Nếu auto_mode: tự động approve, không pause
                if auto_mode:
                    status = "running"
                    # Auto-resume với approve
                    result_auto = graph.invoke(
                        Command(resume={"action": "approve"}),
                        config=config
                    )
                    draft = result_auto.get("draft")
                    usage = result_auto.get("usage", {})
                    status = "completed" if result_auto.get("publish_status") == "published" else "paused"
                    break
                
                # Normal mode: pause chờ user
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
                "session_id": session_id,
                "status": s.status,
                "draft": s.draft,
                "publish_status": s.publish_status,
                "approved": bool(s.approved),
                "usage": s.usage,
                "error": s.error
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

            # Lưu version history (cho Màn 4 Diff Review)
            current_draft = result_graph.get("draft")
            if current_draft:
                versions = s.draft.get("versions", []) if s.draft else []
                versions.append({
                    "version": len(versions) + 1,
                    "content": current_draft["content"],
                    "metadata": current_draft["metadata"],
                    "action": action
                })
                current_draft["versions"] = versions

            s.status = "completed"
            s.approved = 1 if result_graph.get("approved") else 0
            s.publish_status = result_graph.get("publish_status")
            s.draft = current_draft
            s.usage = result_graph.get("usage")
            s.error = result_graph.get("error")

            await db.commit()

            return {
                "session_id": session_id,
                "status": "completed",
                "draft": s.draft,
                "publish_status": s.publish_status,
                "approved": bool(s.approved),
                "usage": s.usage,
                "error": s.error
            }

    # ══════════════════════════════════════════════════════════════
    # CHAT API (Mới — Phương án C: Inline AI + Chat Sidebar)
    # ══════════════════════════════════════════════════════════════

    async def chat_edit(self, draft: str, instruction: str) -> dict:
        """Chat sidebar: rewrite toàn bộ draft."""
        new_draft = call_groq(
            f"Original draft:\n{draft}\n\n"
            f"Instruction: {instruction}\n\n"
            f"Rewrite entire draft following instruction. Keep tone, style, brand voice. "
            f"Return only the new draft, no explanation.",
            max_tokens=800
        )

        # Tính token ước lượng
        tokens = len(new_draft.split()) * 2

        return {
            "draft": new_draft,
            "usage": {"tokens": tokens, "type": "chat_edit", "cost": tokens * 0.00001}
        }

    async def chat_inline(self, paragraph: str, instruction: str, context: str) -> dict:
        """Inline AI: rewrite đoạn bôi đen, giữ context toàn bài."""
        new_paragraph = call_groq(
            f"Full article context:\n{context}\n\n"
            f"Paragraph to rewrite:\n{paragraph}\n\n"
            f"Instruction: {instruction}\n\n"
            f"Rewrite ONLY this paragraph. Match tone with full article. "
            f"Return only the rewritten paragraph, no explanation.",
            max_tokens=200
        )

        tokens = len(new_paragraph.split()) * 2

        # Tạo diff để UI highlight
        changes = [{
            "type": "replace",
            "old": paragraph,
            "new": new_paragraph,
            "position": "inline"
        }]

        return {
            "draft": new_paragraph,  # Chỉ đoạn mới
            "usage": {"tokens": tokens, "type": "chat_inline", "cost": tokens * 0.00001},
            "changes": changes
        }

    async def get_versions(self, session_id: str) -> dict:
        """Lấy version history cho Màn 4 (Diff Review)."""
        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s = result.scalars().first()

            if not s or not s.draft:
                return None

            versions = s.draft.get("versions", [])
            current = s.draft.get("version", 1)

            return {
                "session_id": session_id,
                "versions": versions,
                "current_version": current
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