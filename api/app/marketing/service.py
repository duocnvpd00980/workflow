import uuid
from sqlalchemy import select, func
from sqlalchemy.orm.attributes import flag_modified  # ← THÊM ĐỂ FIX LỖI UPDATE JSON
from langgraph.types import Command

from app.marketing.nodes import call_groq
from app.db import AsyncSessionLocal
from .models import WorkflowSession
from .workflow import graph
from app.tasks import create_task, finish_task, fail_task, update_task


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
            "error": None,
            "memory_history": []  # Khởi tạo mảng rỗng ban đầu
        }

        async with AsyncSessionLocal() as db:
            session = WorkflowSession(
                id=session_id,
                thread_id=thread_id,
                request=request,
                status="running",
                draft=None,
                usage={"total_tokens": 0, "total_cost": 0.0},
                publish_status=None,
                approved=0,
                error=None
            )
            db.add(session)
            await db.commit()

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

            async with AsyncSessionLocal() as db:
                await fail_task(db, bg_task_id, error_message=error_msg)
            raise

        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s = result.scalars().first()
            if s:
                s.status = status
                s.draft = draft
                # Đảm bảo giữ cấu trúc usage thống nhất
                if s.usage:
                    s.usage.update(usage or {})
                else:
                    s.usage = usage
                flag_modified(s, "usage")
                await db.commit()

        async with AsyncSessionLocal() as db:
            if status == "paused":
                await update_task(db, bg_task_id, steps_done=1)
            elif status == "completed":
                await finish_task(db, bg_task_id, steps_done=2)

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

            # 🌟 ĐIỂM SỬA CHẾT NGƯỜI: Đồng bộ ngược Draft từ DB vào LangGraph trước khi chạy tiếp
            # Mục đích: Đảm bảo bài viết đã sửa qua Chat-API được nạp thẳng làm ngữ cảnh cho luồng duyệt/xuất bản
            if s.draft:
                await graph.update_state(
                    config,
                    {
                        "draft": s.draft,
                        "memory_history": s.draft.get("memory_history", [])
                    }
                )

            resume_cmd = {"action": action}
            if action == "edit" and content:
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
            
            # Cập nhật usage an toàn
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
                await finish_task(db, bg_task.id, steps_done=2)

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
    # CHAT API — ĐÃ TỐI ƯU HÓA HIỆU NĂNG & THỐNG NHẤT BỘ NHỚ
    # ══════════════════════════════════════════════════════════════

    async def chat_edit(self, session_id: str, instruction: str) -> dict:
        """Sửa toàn bộ bản phác thảo dựa trên yêu cầu và nạp vào lịch sử memory."""
        # Bước 1: Mở DB thật nhanh lấy dữ liệu cũ rồi đóng lại ngay để giải phóng connection
        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s = result.scalars().first()
            if not s or not s.draft:
                raise ValueError("Không tìm thấy session hoặc bản draft để sửa.")
            
            old_draft = s.draft
            old_content = old_draft.get("content", "")

        # Bước 2: Gọi AI bên ngoài transaction DB (Tránh block connection pool)
        new_content = call_groq(
            f"Original draft:\n{old_content}\n\n"
            f"Instruction: {instruction}\n\n"
            f"Rewrite entire draft following instruction. Keep tone, style, brand voice. "
            f"Return only the new draft, no explanation.",
            max_tokens=800
        )
        tokens = len(new_content.split()) * 2
        usage_data = {"tokens": tokens, "type": "chat_edit", "cost": tokens * 0.00001}

        # Bước 3: Mở lại DB để ghi nhận kết quả và đồng bộ bộ nhớ
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

        return {"session_id": session_id, "draft": updated_draft, "usage": usage_data}

    async def chat_inline(self, session_id: str, paragraph: str, instruction: str) -> dict:
        """Sửa một đoạn văn đơn lẻ, thay thế trong bài viết tổng và nạp bộ nhớ."""
        # Bước 1: Lấy context bài viết
        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowSession).filter_by(id=session_id)
            result = await db.execute(stmt)
            s = result.scalars().first()
            if not s or not s.draft:
                raise ValueError("Không tìm thấy dữ liệu bài viết để sửa đoạn văn.")
            
            old_draft = s.draft
            full_context = old_draft.get("content", "")

        # Bước 2: Gọi AI chỉnh sửa đoạn biệt lập bên ngoài transaction
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

        # Bước 3: Lưu lại dữ liệu chỉnh sửa vào DB
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

    async def list_sessions(self, status: str = None, limit: int = 20, offset: int = 0) -> dict:
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