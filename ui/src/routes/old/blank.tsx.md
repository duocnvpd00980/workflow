import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/blank')({
  component: BlankPage,
})

function BlankPage() {
  return (
    <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
      Chọn một mục từ menu bên trái để bắt đầu.
    </div>
  );
}