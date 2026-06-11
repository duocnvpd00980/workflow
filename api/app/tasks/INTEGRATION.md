# Tích hợp tasks/ vào 3 module

## 1. Đăng ký trong db.py

```python
# app/db.py — thêm vào init_db()
from app.tasks.models import Base as TaskBase

async def init_db() -> None:
    ...
    async with engine.begin() as conn:
        await conn.run_sync(TaskBase.metadata.create_all)  # thêm dòng này
        await conn.run_sync(ChatBase.metadata.create_all)
        ...
```

## 2. Đăng ký router trong main.py

```python
from app.tasks.router import router as tasks_router
app.include_router(tasks_router)
```

---

## 3. Marketing — app/marketing/service.py

Trong hàm `start()`, wrap lại như sau:

```python
from app.tasks import create_task, finish_task, fail_task

async def start(self, request: str, brand_id: str, auto_mode: bool):
    # ... logic hiện tại tạo session_id ...

    # Thêm: tạo task record
    async with AsyncSessionLocal() as db:
        bg_task = await create_task(
            db,
            source="marketing",
            source_id=session_id,
            title=request[:200],
            triggered_by="user",
            steps_total=5,          # số bước workflow của bạn
            model="Claude 4 Sonnet",
        )
        task_id = bg_task.id

    # ... chạy workflow như cũ ...

    # Thêm: cập nhật khi xong
    async with AsyncSessionLocal() as db:
        await finish_task(db, task_id, steps_done=5)

    # Thêm: cập nhật khi lỗi (trong except)
    # async with AsyncSessionLocal() as db:
    #     await fail_task(db, task_id, error_message=str(e))
```

---

## 4. Hotel Research — app/research/service.py

Trong hàm `pipeline_worker_task()`, thêm vào đầu và cuối:

```python
from app.tasks import create_task, finish_task, fail_task

async def pipeline_worker_task(task_id, business_name, address, industry):
    # Thêm: tạo task record
    async with AsyncSessionLocal() as db:
        bg_task = await create_task(
            db,
            source="research",
            source_id=task_id,
            title=f"Nghiên cứu: {business_name}",
            triggered_by="user",
            steps_total=6,          # số node trong pipeline
        )
        bg_task_id = bg_task.id

    try:
        # ... logic pipeline hiện tại ...

        # Thêm: cập nhật từng bước nếu muốn (tuỳ chọn)
        async with AsyncSessionLocal() as db:
            await update_task(db, bg_task_id, steps_done=3)

        # ... tiếp tục ...

        async with AsyncSessionLocal() as db:
            await finish_task(db, bg_task_id, steps_done=6)

    except Exception as e:
        async with AsyncSessionLocal() as db:
            await fail_task(db, bg_task_id, error_message=str(e))
        raise
```

---

## 5. RAG — app/rag/router.py

Trong các endpoint `upload()`, `crawl()`, `crawl_business()`:

```python
from app.tasks import create_task, finish_task, fail_task

# Trong upload():
async with AsyncSessionLocal() as db:
    bg_task = await create_task(
        db,
        source="rag",
        source_id=str(doc.id),
        title=f"Upload: {title}",
        triggered_by="user",
        steps_total=1,
    )

# ... xử lý như cũ ...

async with AsyncSessionLocal() as db:
    await finish_task(db, bg_task.id, steps_done=1)

# Tương tự cho crawl() và crawl_business()
```

---

## Lưu ý

- Mỗi module dùng `AsyncSessionLocal` riêng khi gọi tasks service,
  không dùng chung db session với logic nghiệp vụ để tránh conflict transaction.
- `source_id` lưu id gốc của từng module để UI có thể link về đúng trang chi tiết.
- `steps_done` / `steps_total` là tuỳ chọn — để 0 nếu module không track được bước.
