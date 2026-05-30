from .interrupt_sync_protocol import InterruptSyncOutput


class InterruptSyncService:
    async def run(
        self,
        completed_modules: list[str] | None,
        active_branches: list[str] | None,
    ) -> InterruptSyncOutput:

        # Normalize
        completed_modules = completed_modules or []
        active_branches = active_branches or []

        # Remove duplicates
        completed_set = set(completed_modules)
        active_set = set(active_branches)

        # Nếu không có branch nào => auto complete
        if not active_set:
            return InterruptSyncOutput(
                active_branches=[],
                completed_modules=[],
                pending_modules=[],
                is_sync_complete=True,
                checkpoint_note="Không có branch cần đồng bộ.",
            )

        pending_modules = sorted(list(active_set - completed_set))

        is_sync_complete = len(pending_modules) == 0

        return InterruptSyncOutput(
            active_branches=sorted(list(active_set)),
            completed_modules=sorted(list(completed_set)),
            pending_modules=pending_modules,
            is_sync_complete=is_sync_complete,
            synchronization_mode="dynamic_barrier",
            checkpoint_note=(
                "Tất cả branch đã hoàn thành."
                if is_sync_complete
                else f"Đang chờ: {', '.join(pending_modules)}"
            ),
        )
