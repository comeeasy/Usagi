// TODO: 레이아웃 선택/줌/필터 버튼
// 레이아웃: dagre, circle, grid, concentric
// 줌인/줌아웃/핏 버튼
// 노드 타입 필터 (Concept / Individual 토글)

interface GraphControlsProps {
  onLayoutChange?: (layout: string) => void
  onZoomIn?: () => void
  onZoomOut?: () => void
  onFit?: () => void
  onFilterChange?: (filter: { concepts: boolean; individuals: boolean }) => void
}

export default function GraphControls({
  onLayoutChange,
  onZoomIn,
  onZoomOut,
  onFit,
  onFilterChange,
}: GraphControlsProps) {
  return (
    <div className="flex gap-2 p-2 bg-bg-elevated border border-border rounded">
      {/* TODO: layout selector, zoom buttons, filter toggles */}
    </div>
  )
}
