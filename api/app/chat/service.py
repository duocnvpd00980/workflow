from __future__ import annotations
import json
import uuid
import logging
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.chat.models import Message
from app.chat.nodes import load_contexts, save_result, _build_prompt
from app.llm_clients import stream_groq

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self):
        self._stopped_convs = set()

    async def mark_as_stopped(self, conversation_id: uuid.UUID):
        self._stopped_convs.add(conversation_id)

    async def check_if_stopped(self, conversation_id: uuid.UUID) -> bool:
        return conversation_id in self._stopped_convs

    async def clear_stop_flag(self, conversation_id: uuid.UUID):
        self._stopped_convs.discard(conversation_id)

    async def stream_graph(
        self,
        message: str,
        msg_id: uuid.UUID,
        conversation_id: uuid.UUID,
        db: AsyncSession,
        brand_id: Optional[str] = None,
        business_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:

        state = {
            "content_draft": "",
            "instruction": message,
            "session_id": str(conversation_id),
            "conversation_id": str(conversation_id),
            "msg_id": str(msg_id),
            "brand_id": brand_id,
            "business_id": business_id,
            "brand_profile": {},
            "brand_context": "",
            "knowledge_rag": [],
            "rag_context": "",
            "conversation_history": [],
            "history_context": "",
            "rewritten_text": "",
            "original_draft": "",
            "saved": False,
            "error": None,
        }

        try:
            # Bước 1: load brand, RAG, history song song trong 1 node
            context_result = await load_contexts(state)
            state.update(context_result)

            # Bước 2: build prompt rồi stream Groq trực tiếp — token by token
            prompt = _build_prompt(state)
            full_text: list[str] = []

            async for token in stream_groq(prompt, max_tokens=2000):
                if await self.check_if_stopped(conversation_id):
                    break
                full_text.append(token)
                yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"

            # Bước 3: save toàn bộ text vào DB
            state["rewritten_text"] = "".join(full_text)
            save_state = await save_result(state)

            if not save_state.get("saved"):
                logger.warning(f"Save failed: {save_state.get('error')}")

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        finally:
            await self.clear_stop_flag(conversation_id)

    async def resume_graph(
        self,
        action: str,
        feedback: str,
        msg_id: uuid.UUID,
        conversation_id: uuid.UUID,
        db: AsyncSession,
    ) -> AsyncGenerator[str, None]:
        yield f"data: {json.dumps({'status': 'resumed'})}\n\n"

    async def restore_session(self, conversation_id: uuid.UUID, db: AsyncSession) -> list[dict]:
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.status == "completed",
            )
            .order_by(Message.created_at.asc())
        )
        result = await db.execute(stmt)
        messages = result.scalars().all()

        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
            }
            for m in messages
        ]