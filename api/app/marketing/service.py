import json
from typing import Any, Dict, Optional
import uuid
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func
from sqlalchemy.orm.attributes import flag_modified
from langgraph.types import Command
from typing import Tuple, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import AsyncSessionLocal
from app.marketing.nodes import call_groq, call_groq_stream
from .models import WorkflowSession
from .graphs import get_graph  # ✅ Import registry
from app.tasks import create_task, finish_task, fail_task, update_task
import re
import unicodedata


logger = logging.getLogger(__name__)



# ─── PRE-FILTER (zero token cost) ───
_KNOWN_GIBBERISH = frozenset({
    "asd", "asdf", "asdfasdf", "asdasd", "adasd", "qwe", "qwerty",
    "qwertyuiop", "zxcvbn", "lkj", "dsfsdf", "test", "testtest",
    "abc", "abcabc", "abc123", "123123", "xyz", "aaa", "111",
})


def _strip_diacritics(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))

def _is_trivially_meaningless(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 2:
        return True
    if re.match(r"^[\W\d]*$", stripped):
        return True
    if len(set(stripped.lower())) == 1:
        return True
    normalized = _strip_diacritics(stripped.lower())
    normalized = re.sub(r"[^a-z0-9]", "", normalized)
    if normalized in _KNOWN_GIBBERISH:
        return True
    return False


_FALLBACK_CLARIFICATION = {
    "message": (
        "Ý tưởng bạn nhập đang quá ngắn hoặc chưa rõ nghĩa để hệ thống hiểu đúng. "
        "Vui lòng quay lại và mô tả cụ thể hơn: chủ đề, mục tiêu bài viết, và đối tượng đọc."
    ),
    "options": [],
}


class WorkflowService:
    def __init__(self):
        self._running_tasks: dict[str, asyncio.Task] = {}

    def create_session(self) -> str:
        return str(uuid.uuid4())[:8]

    async def start_queued(
        self,
        request: str,
        brand_id: str,
        group: str = "blog_web",  # ✅ Thêm group để chọn graph
        function: str = "blog_post",  # ✅ Thêm function
        auto_mode: bool = False,
        selected_option_text: Optional[str] = None,
    ) -> str:
        """
        Tạo session, lưu DB với status='queued', rồi bắt đầu chạy ngầm.
        """
        session_id = self.create_session()
        thread_id = f"wf-{uuid.uuid4().hex[:6]}"

        # Lưu DB ngay với status 'queued'
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

        # Tạo background task
        task = asyncio.create_task(
            self._run_workflow_background(
                session_id, thread_id, request, brand_id, group, function, auto_mode
            )
        )
        self._running_tasks[session_id] = task

        def _cleanup(t: asyncio.Task):
            self._running_tasks.pop(session_id, None)
            if t.exception():
                logger.error(f"[BG TASK FAILED] {session_id}: {t.exception()}")

        task.add_done_callback(_cleanup)

        return session_id


    async def check_request_ambiguity(
        self,
        request_text: str,
        brand_id: str | None = None,
        db: AsyncSession | None = None,
        ) -> tuple[bool, dict[str, Any] | None]:


        text = (request_text or "").strip()

        # Fast reject bằng rule
        if _is_trivially_meaningless(text):
            return True, _FALLBACK_CLARIFICATION

        brand_context = ""
        try:
            db_session = db or getattr(self, "db", None)

            if brand_id and db_session:
                from app.brand.brand_voice_prompt import (
                    get_brand_context_summary,
                )

                brand_context = (
                    await get_brand_context_summary(
                        brand_id,
                        db_session,
                    )
                )
        except Exception:
            logger.exception(
                "[AMBIGUITY] load brand context failed"
            )

        prompt = f"""
        ```

        Bạn là bộ phân loại.

        {f"Context: {brand_context}" if brand_context else ""}

        Input:
        {text}

        Luật:

        * VAGUE → vô nghĩa, ký tự rác, không có chủ đề
        * CLEAR → có thể tạo nội dung dù thiếu chi tiết

        Ví dụ:
        viết blog về biển -> CLEAR
        quảng bá spa -> CLEAR
        123### -> VAGUE

        CHỈ trả:
        CLEAR

        hoặc

        VAGUE|<message>
        """.strip()


        try:
            import asyncio

            resp = await asyncio.to_thread(
                call_groq,
                prompt=prompt,
                max_tokens=60,
            )

            result = (resp or "").strip()

            logger.info(
                "[AMBIGUITY] input=%s result=%s",
                text,
                result,
            )

            if result.upper().startswith("VAGUE"):
                parts = result.split("|", 1)

                return (
                    True,
                    {
                        "message": (
                            parts[1].strip()
                            if len(parts) > 1
                            else _FALLBACK_CLARIFICATION["message"]
                        ),
                        "options": (
                            _FALLBACK_CLARIFICATION["options"]
                        ),
                    },
                )

            return False, None

        except Exception:
            logger.exception(
                "[AMBIGUITY CHECK FAILED]"
            )

            return False, None



        
    async def _run_workflow_background(
        self,
        session_id: str,
        thread_id: str,
        request: str,
        brand_id: str,
        group: str,
        function: str,
        auto_mode: bool,
    ) -> None:
        try:
            await self._async_run_workflow(
                session_id, thread_id, request, brand_id, group, function, auto_mode
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

    def _sync_run_workflow(
        self,
        session_id: str,
        thread_id: str,
        request: str,
        brand_id: str,
        group: str,  # ✅ Thêm group
        function: str,  # ✅ Thêm function
        auto_mode: bool,
    ) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                self._async_run_workflow(session_id, thread_id, request, brand_id, group, function, auto_mode)
            )
        finally:
            loop.close()


    async def _async_run_workflow(
        self,
        session_id: str,
        thread_id: str,
        request: str,
        brand_id: str,
        group: str,
        function: str,
        auto_mode: bool,
    ) -> None:
        """
        Logic chạy workflow thực tế.
        """
        graph = get_graph(group)

        config = {
            "configurable": {"thread_id": thread_id},
            "run_name": f"{group}_{function}",
            "tags": ["marketing", group],
            "metadata": {"session_id": session_id, "brand_id": brand_id},
        }

        logger.info(f"[LANGSMITH] invoke graph | session={session_id}")

        draft, status, usage = None, "running", {}
        final_state = {}  # ✅ capture state cuối từ graph

        initial_state = {
            "session_id": session_id,
            "brand_id": brand_id,
            "request": request,
            "function": function,
            "group": group,
            "brand_profile": {},
            "length": "vừa",
            "tone": "chuyên nghiệp",
            "needs_image": False,
            "system_prompt": "",
            "enriched_topic": "",
            "title": None,
            "content": None,
            "seo_meta": None,
            "image_url": None,
            "draft": None,
            "approved": False,
            "revision_note": None,
            "usage": {},
            "error": None,
            "memory_history": [],
            "publish_status": "pending",
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
            async for event in graph.astream(initial_state, config=config):

                # ✅ Luôn capture state mới nhất từ mỗi node output
                for node_name, node_output in event.items():
                    if node_name != "__interrupt__" and isinstance(node_output, dict):
                        final_state = node_output

                if "__interrupt__" in event:
                    if auto_mode:
                        result_auto = await graph.ainvoke(
                            Command(resume={"action": "approve"}),
                            config=config,
                        )
                        draft  = result_auto.get("draft")
                        usage  = result_auto.get("usage", {})
                        status = "completed" if result_auto.get("publish_status") == "published" else "paused"
                        break

                    status = "paused"
                    data   = event["__interrupt__"][0].value
                    draft  = data.get("draft")
                    usage  = data.get("usage", {})

                    current_state = await graph.aget_state(config)
                    if draft:
                        draft["_graph_state"] = {**current_state.values}
                    break

        except Exception as e:
            status    = "error"
            error_msg = str(e)[:50]

            async with AsyncSessionLocal() as db:
                stmt   = select(WorkflowSession).filter_by(id=session_id)
                result = await db.execute(stmt)
                s      = result.scalars().first()
                if s:
                    s.status = "error"
                    s.error  = error_msg
                    await db.commit()

            async with AsyncSessionLocal() as db:
                await fail_task(db, bg_task_id, error_message=error_msg)
            return

        # ✅ Graph kết thúc không qua interrupt → đọc status thật từ final_state
        if status == "running":
            graph_status = final_state.get("status")
            graph_error  = final_state.get("error")

            if graph_status == "failed" or graph_error:
                status = "failed"
            else:
                status = "completed"

            draft = final_state.get("draft")
            usage = final_state.get("usage", {})

        # Cập nhật kết quả cuối cùng
        async with AsyncSessionLocal() as db:
            stmt   = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s      = result.scalars().first()
            if s:
                # ✅ Không ghi đè nếu blog_handle_error đã set failed/error trước rồi
                if s.status not in ("failed", "error"):
                    s.status = status

                s.draft = draft
                if s.usage:
                    s.usage.update(usage or {})
                else:
                    s.usage = usage
                flag_modified(s, "usage")
                await db.commit()

        # Cập nhật background task log
        async with AsyncSessionLocal() as db:
            if status == "paused":
                await update_task(db, bg_task_id, status="paused", steps_done=2, steps_total=2)
            elif status == "completed":
                await finish_task(db, bg_task_id, steps_done=2)
            elif status in ("failed", "error"):
                await fail_task(
                    db,
                    bg_task_id,
                    error_message=final_state.get("error") or status,
                )





    async def start(self, request: str, brand_id: str, group: str = "blog_web", function: str = "blog_post", auto_mode: bool = False) -> dict:
        """Giữ lại cho backward compatibility."""
        session_id = await self.start_queued(request, brand_id, group, function, auto_mode)
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

    async def resume(self, session_id: str, action: str, content: str = None, group: str = "blog_web") -> dict:
        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s = result.scalars().first()
            if not s:
                return None

            config = {"configurable": {"thread_id": s.thread_id}}

            # ✅ Chọn graph động
            graph = get_graph(group)

            if s.draft:
                restore = s.draft.get("_graph_state", {})

                graph.update_state(
                    config,
                    {
                        **restore,
                        "draft": s.draft,
                        "memory_history": s.draft.get(
                            "memory_history",
                            []
                        ),
                    }
                )

            resume_cmd = {"action": action}
            if content:
                resume_cmd["content"] = content

            result_graph = await graph.ainvoke(Command(resume=resume_cmd), config=config)

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
                else:
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

        graph_state = old_draft.get("_graph_state", {})

        prompt = f"""
        Original request:
        {graph_state.get("request","")}

        Brand prompt:
        {graph_state.get("system_prompt","")}

        Current article:
        {old_content}

        Edit instruction:
        {instruction}

        Rewrite ENTIRE article.

        Rules:
        - Keep original topic
        - Keep brand voice
        - Keep article structure
        - Apply only instruction
        - Return article only
        """

        new_content = call_groq(
            prompt,
            max_tokens=2000
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
                **old_draft,
                "content": new_content,
                "versions": versions,
                "memory_history": memory_history,
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
        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s = result.scalars().first()
            if not s or not s.draft:
                raise ValueError("Không tìm thấy session hoặc bản draft.")
            
            old_content = s.draft.get("content", "")

        prompt = (
            f"Original draft:\n{old_content}\n\n"
            f"Instruction: {instruction}\n\n"
            f"Rewrite entire draft following instruction. Keep tone, style, brand voice. "
            f"Return only the new draft, no explanation."
        )
        
        full_response = ""
        async for chunk in call_groq_stream(prompt, max_tokens=800):
            full_response += chunk
            yield chunk
        
        tokens = len(full_response.split()) * 2
        usage_data = {"tokens": tokens, "type": "chat_edit", "cost": tokens * 0.00001}
        
        async with AsyncSessionLocal() as db:
            pass
        
        yield "[DONE]"

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