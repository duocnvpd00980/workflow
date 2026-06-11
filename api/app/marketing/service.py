import uuid
from sqlalchemy import select
from langgraph.types import Command

from app.marketing.nodes import call_groq
from app.db import AsyncSessionLocal
from .models import WorkflowSession
from .workflow import graph
from sqlalchemy import func
from app.tasks import create_task, finish_task, fail_task, update_task  # ← THÊM


class WorkflowService:
    def create_session(self) -> str:
        return str(uuid.uuid4())[:8]

    async def start(self, request: str, brand_id: str, auto_mode: bool = False) -> dict:
        thread_id = f"wf-{uuid.uuid4().hex[:6]}"
        config = {"configurable": {"thread_id": thread_id}}
        session_id = self.create_session()

        draft, status, usage = None, "running", {}

        initial_state = {
            "session_id": session_id,
            "brand_id": brand_id,
            "request": request,
            "template": None,
            "context": {},
            "draft": None,
            "approved": False,
            "publish_status": None,
            "usage": {},
            "error": None
        }

        # Lưu WorkflowSession DB
        async with AsyncSessionLocal() as db:
            session = WorkflowSession(
                id=session_id,
                thread_id=thread_id,
                request=request,
                status="running",
                draft=None,
                usage={},
                publish_status=None,
                approved=0,
                error=None
            )
            db.add(session)
            await db.commit()

        # ── Tạo row background_tasks trung tâm ───────────────────
        async with AsyncSessionLocal() as db:
            bg_task = await create_task(
                db,
                source="marketing",
                source_id=session_id,
                title=request[:200],
                triggered_by="user",
                steps_total=2,   # bước 1: generate, bước 2: approve/publish
            )
            bg_task_id = bg_task.id
        # ─────────────────────────────────────────────────────────

        try:
            async for event in graph.astream(initial_state, config=config):
                if "__interrupt__" in event:
                    if auto_mode:
                        status = "running"
                        result_auto = await graph.ainvoke(
                            Command(resume={"action": "approve"}),
                            config=config
                        )
                        draft = result_auto.get("draft")
                        usage = result_auto.get("usage", {})
                        status = "completed" if result_auto.get("publish_status") == "published" else "paused"
                        break

                    status = "paused"
                    data = event["__interrupt__"][0].value
                    draft, usage = data["draft"], data["usage"]
                    break

        except Exception as e:
            status = "error"
            error_msg = str(e)[:50]

            async with AsyncSessionLocal() as db:
                stmt = select(WorkflowSession).filter_by(id=session_id)
                result = await db.execute(stmt)
                s = result.scalars().first()
                if s:
                    s.status = "error"
                    s.error = error_msg
                    await db.commit()

            # ── Đánh dấu thất bại ────────────────────────────────
            async with AsyncSessionLocal() as db:
                await fail_task(db, bg_task_id, error_message=error_msg)
            # ─────────────────────────────────────────────────────
            raise

        # Update WorkflowSession sau khi chạy xong
        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s = result.scalars().first()
            if s:
                s.status = status
                s.draft = draft
                s.usage = usage
                await db.commit()

        # ── Cập nhật background_tasks theo status hiện tại ───────
        async with AsyncSessionLocal() as db:
            if status == "paused":
                # Đang chờ user duyệt — vẫn "running", cập nhật steps_done=1
                await update_task(db, bg_task_id, steps_done=1)
            elif status == "completed":
                await finish_task(db, bg_task_id, steps_done=2)
            elif status == "error":
                pass  # Đã xử lý trong except ở trên
        # ─────────────────────────────────────────────────────────

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

            result_graph = await graph.ainvoke(Command(resume=resume_cmd), config=config)

            # Lưu version history
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

        # ── Đánh dấu hoàn thành khi user resume xong ─────────────
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select as sa_select
            from app.tasks.models import BackgroundTask
            row = await db.execute(
                sa_select(BackgroundTask).where(
                    BackgroundTask.source == "marketing",
                    BackgroundTask.source_id == session_id,
                )
            )
            bg_task = row.scalars().first()
            if bg_task:
                await finish_task(db, bg_task.id, steps_done=2)
        # ─────────────────────────────────────────────────────────

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
    # CHAT API
    # ══════════════════════════════════════════════════════════════

    async def chat_edit(self, draft: str, instruction: str) -> dict:
        new_draft = call_groq(
            f"Original draft:\n{draft}\n\n"
            f"Instruction: {instruction}\n\n"
            f"Rewrite entire draft following instruction. Keep tone, style, brand voice. "
            f"Return only the new draft, no explanation.",
            max_tokens=800
        )
        tokens = len(new_draft.split()) * 2
        return {
            "draft": new_draft,
            "usage": {"tokens": tokens, "type": "chat_edit", "cost": tokens * 0.00001}
        }

    async def chat_inline(self, paragraph: str, instruction: str, context: str) -> dict:
        new_paragraph = call_groq(
            f"Full article context:\n{context}\n\n"
            f"Paragraph to rewrite:\n{paragraph}\n\n"
            f"Instruction: {instruction}\n\n"
            f"Rewrite ONLY this paragraph. Match tone with full article. "
            f"Return only the rewritten paragraph, no explanation.",
            max_tokens=200
        )
        tokens = len(new_paragraph.split()) * 2
        changes = [{
            "type": "replace",
            "old": paragraph,
            "new": new_paragraph,
            "position": "inline"
        }]
        return {
            "draft": new_paragraph,
            "usage": {"tokens": tokens, "type": "chat_inline", "cost": tokens * 0.00001},
            "changes": changes
        }

    async def get_versions(self, session_id: str) -> dict:
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

    async def list_sessions(
        self,
        status: str = None,
        limit: int = 20,
        offset: int = 0
    ) -> dict:
        async with AsyncSessionLocal() as db:
            count_stmt = select(func.count()).select_from(WorkflowSession)
            if status:
                count_stmt = count_stmt.where(WorkflowSession.status == status)
            total = (await db.execute(count_stmt)).scalar()

            stmt = select(WorkflowSession).order_by(WorkflowSession.created_at.desc())
            if status:
                stmt = stmt.where(WorkflowSession.status == status)
            stmt = stmt.limit(limit).offset(offset)
            result = await db.execute(stmt)
            sessions = result.scalars().all()

            return {
                "items": [
                    {
                        "session_id": s.id,
                        "status": s.status,
                        "request": s.request,
                        "draft": s.draft,
                        "publish_status": s.publish_status,
                        "approved": bool(s.approved),
                        "usage": s.usage,
                        "error": s.error,
                        "created_at": s.created_at,
                        "updated_at": s.updated_at,
                    }
                    for s in sessions
                ],
                "total": total,
                "limit": limit,
                "offset": offset,
            }