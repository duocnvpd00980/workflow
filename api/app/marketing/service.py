import uuid
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func
from sqlalchemy.orm.attributes import flag_modified
from langgraph.types import Command

from app.marketing.nodes import call_groq, call_groq_stream
from app.db import AsyncSessionLocal
from .models import WorkflowSession
from .workflow import marketing_graph
from app.tasks import create_task, finish_task, fail_task, update_task

logger = logging.getLogger(__name__)

# Thread pool riêng cho LangGraph (blocking I/O operations)
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="workflow_")


class WorkflowService:
    def __init__(self):
        self._running_tasks: dict[str, asyncio.Task] = {}

    def create_session(self) -> str:
        return str(uuid.uuid4())[:8]

    async def start_queued(self, request: str, brand_id: str, auto_mode: bool = False) -> str:
        """
        Tạo session, lưu DB với status='queued', rồi bắt đầu chạy ngầm.
        Trả về session_id ngay lập tức (không đợi workflow chạy xong).
        """
        session_id = self.create_session()
        thread_id = f"wf-{uuid.uuid4().hex[:6]}"

        # Lưu DB ngay với status 'queued' — trả về ngay lập tức
        async with AsyncSessionLocal() as db:
            from app.chat.models import Conversation
            
            conv = Conversation(title=f"Chat: {request[:50] if request else 'New'}")
            db.add(conv)
            await db.flush()
            await db.refresh(conv)
            
            session = WorkflowSession(
                id=session_id,
                thread_id=thread_id,
                request=request,
                status="queued",
                conversation_id=str(conv.id),
                draft=None,
                usage={"total_tokens": 0, "total_cost": 0.0},
                publish_status=None,
                approved=0,
                error=None
            )
            db.add(session)
            await db.commit()

        # Tạo background task thật sự — không await, chạy song song
        task = asyncio.create_task(
            self._run_workflow_background(session_id, thread_id, request, brand_id, auto_mode)
        )
        self._running_tasks[session_id] = task

        # Cleanup khi xong
        def _cleanup(t: asyncio.Task):
            self._running_tasks.pop(session_id, None)
            if t.exception():
                logger.error(f"[BG TASK FAILED] {session_id}: {t.exception()}")

        task.add_done_callback(_cleanup)

        return session_id

    async def _run_workflow_background(self, session_id: str, thread_id: str, request: str, brand_id: str, auto_mode: bool) -> None:
        """
        Chạy workflow trong thread pool riêng để không block event loop chính.
        """
        loop = asyncio.get_event_loop()

        try:
            # Chạy blocking LangGraph trong thread pool
            await loop.run_in_executor(
                _executor,
                self._sync_run_workflow,
                session_id, thread_id, request, brand_id, auto_mode
            )
        except Exception as e:
            logger.error(f"[BG WORKFLOW FAILED] {session_id}: {e}")
            async with AsyncSessionLocal() as db:
                stmt = select(WorkflowSession).filter_by(id=session_id)
                result = await db.execute(stmt)
                s = result.scalars().first()
                if s:
                    s.status = "error"
                    s.error = str(e)[:50]
                    await db.commit()

    def _sync_run_workflow(self, session_id: str, thread_id: str, request: str, brand_id: str, auto_mode: bool) -> None:
        """
        Hàm đồng bộ chạy trong thread pool.
        Tạo event loop riêng cho thread này để chạy async LangGraph.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(
                self._async_run_workflow(session_id, thread_id, request, brand_id, auto_mode)
            )
        finally:
            loop.close()

    async def _async_run_workflow(self, session_id: str, thread_id: str, request: str, brand_id: str, auto_mode: bool) -> None:
        """
        Logic chạy workflow thực tế (tách từ start() cũ).
        """
        config = {"configurable": {"thread_id": thread_id}}
        draft, status, usage = None, "running", {}

        initial_state = {
            "session_id": session_id,
            "brand_id": brand_id,
            "request": request,
            "template": None,
            "context": {},
            "draft": {"version": 0, "content": "", "metadata": {}},
            "approved": False,
            "publish_status": None,
            "usage": {},
            "error": None,
            "memory_history": []
        }

        # Cập nhật status → running
        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s = result.scalars().first()
            if s:
                s.status = "running"
                await db.commit()

        # Tạo background task log
        async with AsyncSessionLocal() as db:
            bg_task = await create_task(
                db,
                source="marketing",
                source_id=session_id,
                title=request[:200],
                triggered_by="user",
                steps_total=2,
            )
            bg_task_id = bg_task.id

        try:
            async for event in marketing_graph.astream(initial_state, config=config):
                if "__interrupt__" in event:
                    if auto_mode:
                        status = "running"
                        result_auto = await marketing_graph.ainvoke(
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

            async with AsyncSessionLocal() as db:
                await fail_task(db, bg_task_id, error_message=error_msg)
            return

        # Cập nhật kết quả cuối cùng
        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s = result.scalars().first()
            if s:
                s.status = status
                s.draft = draft
                if s.usage:
                    s.usage.update(usage or {})
                else:
                    s.usage = usage
                flag_modified(s, "usage")
                await db.commit()

        async with AsyncSessionLocal() as db:
            if status == "paused":
                await update_task(db, bg_task_id, status="paused", steps_done=2, steps_total=2)
            elif status == "completed":
                await finish_task(db, bg_task_id, steps_done=2)
            elif status == "error":
                await fail_task(db, bg_task_id, error_message=error_msg)

    # ══════════════════════════════════════════════════════════════
    # CÁC METHOD CŨ GIỮ NGUYÊN
    # ══════════════════════════════════════════════════════════════

    async def start(self, request: str, brand_id: str, auto_mode: bool = False) -> dict:
        """Giữ lại cho backward compatibility nếu cần chạy đồng bộ."""
        session_id = await self.start_queued(request, brand_id, auto_mode)
        # Đợi task hoàn thành (không khuyến khích dùng)
        if session_id in self._running_tasks:
            try:
                await asyncio.wait_for(self._running_tasks[session_id], timeout=120)
            except asyncio.TimeoutError:
                pass
        return await self.get_status(session_id)
    
    async def get_status(self, session_id, db=None) -> dict:
        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s = result.scalars().first()
            if not s:
                return None
            return {
                "session_id": session_id,
                "status": s.status,
                "conversation_id": s.conversation_id,
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

            if s.draft:
                marketing_graph.update_state(
                    config,
                    {
                        "draft": s.draft,
                        "memory_history": s.draft.get("memory_history", [])
                    }
                )

            resume_cmd = {"action": action}
            if action == "edit" and content:
                resume_cmd["content"] = content

            result_graph = await marketing_graph.ainvoke(Command(resume=resume_cmd), config=config)

            current_draft = result_graph.get("draft") or s.draft
            if current_draft:
                versions = current_draft.get("versions", [])
                versions.append({
                    "version": len(versions) + 1,
                    "content": current_draft.get("content", ""),
                    "metadata": current_draft.get("metadata", {}),
                    "action": action
                })
                current_draft["versions"] = versions

            s.status = "completed"
            s.approved = 1 if result_graph.get("approved") else 0
            s.publish_status = result_graph.get("publish_status")
            s.draft = current_draft
            
            graph_usage = result_graph.get("usage") or {}
            total_usage = s.usage or {}
            total_usage["total_tokens"] = total_usage.get("total_tokens", 0) + graph_usage.get("total_tokens", 0)
            s.usage = total_usage
            
            s.error = result_graph.get("error")
            
            flag_modified(s, "draft")
            flag_modified(s, "usage")
            await db.commit()

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
                if action == "approve":
                    await finish_task(db, bg_task.id, steps_done=2)
                elif action == "reject":
                    await update_task(db, bg_task.id, status="stopped", steps_done=2, steps_total=2)
                else:  # edit
                    await update_task(db, bg_task.id, status="paused", steps_done=2, steps_total=2)

        return {
            "session_id": session_id,
            "status": "completed",
            "draft": s.draft,
            "publish_status": s.publish_status,
            "approved": bool(s.approved),
            "usage": s.usage,
            "error": s.error
        }

    async def chat_edit(self, session_id: str, instruction: str) -> dict:
        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s = result.scalars().first()
            if not s or not s.draft:
                raise ValueError("Không tìm thấy session hoặc bản draft để sửa.")
            
            old_draft = s.draft
            old_content = old_draft.get("content", "")

        new_content = call_groq(
            f"Original draft:\n{old_content}\n\n"
            f"Instruction: {instruction}\n\n"
            f"Rewrite entire draft following instruction. Keep tone, style, brand voice. "
            f"Return only the new draft, no explanation.",
            max_tokens=800
        )
        tokens = len(new_content.split()) * 2
        usage_data = {"tokens": tokens, "type": "chat_edit", "cost": tokens * 0.00001}

        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s = result.scalars().first()

            versions = old_draft.get("versions", [])
            versions.append({
                "version": len(versions) + 1,
                "content": old_content,
                "metadata": old_draft.get("metadata", {}),
                "action": "chat_edit",
                "instruction": instruction
            })

            memory_history = old_draft.get("memory_history", [])
            memory_history.append({
                "role": "user",
                "feedback": instruction,
                "previous_content": old_content,
                "improved_content": new_content
            })

            updated_draft = {
                "content": new_content,
                "metadata": old_draft.get("metadata", {}),
                "versions": versions,
                "memory_history": memory_history
            }

            s.draft = updated_draft
            
            total_usage = s.usage or {}
            total_usage["total_tokens"] = total_usage.get("total_tokens", 0) + tokens
            s.usage = total_usage

            flag_modified(s, "draft")
            flag_modified(s, "usage")
            await db.commit()

        return {"session_id": session_id, "draft": new_content, "usage": usage_data}


    async def chat_edit_stream(self, session_id: str, instruction: str):
        """Stream edit response — yield từng token."""
        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s = result.scalars().first()
            if not s or not s.draft:
                raise ValueError("Không tìm thấy session hoặc bản draft.")
            
            old_content = s.draft.get("content", "")

        # Stream từ Groq
        prompt = (
            f"Original draft:\n{old_content}\n\n"
            f"Instruction: {instruction}\n\n"
            f"Rewrite entire draft following instruction. Keep tone, style, brand voice. "
            f"Return only the new draft, no explanation."
        )
        
        # Yield từng chunk
        full_response = ""
        async for chunk in call_groq_stream(prompt, max_tokens=800):
            full_response += chunk
            yield chunk
        
        # Lưu vào DB sau khi xong
        tokens = len(full_response.split()) * 2
        usage_data = {"tokens": tokens, "type": "chat_edit", "cost": tokens * 0.00001}
        
        async with AsyncSessionLocal() as db:
            # ... lưu version, memory_history, draft ...
            pass
        
        yield "[DONE]"  # Signal kết thúc


    async def chat_inline(self, session_id: str, paragraph: str, instruction: str) -> dict:
        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s = result.scalars().first()
            if not s or not s.draft:
                raise ValueError("Không tìm thấy dữ liệu bài viết để sửa đoạn văn.")
            
            old_draft = s.draft
            full_context = old_draft.get("content", "")

        new_paragraph = call_groq(
            f"Full article context:\n{full_context}\n\n"
            f"Paragraph to rewrite:\n{paragraph}\n\n"
            f"Instruction: {instruction}\n\n"
            f"Rewrite ONLY this paragraph. Match tone with full article. "
            f"Return only the rewritten paragraph, no explanation.",
            max_tokens=200
        )
        tokens = len(new_paragraph.split()) * 2
        usage_data = {"tokens": tokens, "type": "chat_inline", "cost": tokens * 0.00001}

        if paragraph in full_context:
            new_full_content = full_context.replace(paragraph, new_paragraph, 1)
        else:
            new_full_content = full_context + f"\n\n[Edited]: {new_paragraph}"

        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s = result.scalars().first()

            versions = old_draft.get("versions", [])
            versions.append({
                "version": len(versions) + 1,
                "content": full_context,
                "metadata": old_draft.get("metadata", {}),
                "action": "chat_inline",
                "instruction": f"Sửa đoạn: '{paragraph[:30]}...' thành '{instruction}'"
            })

            memory_history = old_draft.get("memory_history", [])
            memory_history.append({
                "role": "user",
                "feedback": f"Tại đoạn văn: '{paragraph[:40]}', hãy sửa lại: {instruction}",
                "previous_content": paragraph,
                "improved_content": new_paragraph
            })

            updated_draft = {
                "content": new_full_content,
                "metadata": old_draft.get("metadata", {}),
                "versions": versions,
                "memory_history": memory_history
            }
            s.draft = updated_draft
            
            total_usage = s.usage or {}
            total_usage["total_tokens"] = total_usage.get("total_tokens", 0) + tokens
            s.usage = total_usage

            flag_modified(s, "draft")
            flag_modified(s, "usage")
            await db.commit()

        return {
            "session_id": session_id,
            "draft": updated_draft,
            "usage": usage_data,
            "changes": [{"type": "replace", "old": paragraph, "new": new_paragraph, "position": "inline"}]
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

    async def list_sessions(self, status=None, limit=20, offset=0, db=None):
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
                        "conversation_id": s.conversation_id,
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