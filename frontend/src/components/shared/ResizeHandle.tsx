import { PanelResizeHandle } from 'react-resizable-panels'

interface ResizeHandleProps {
  direction?: 'horizontal' | 'vertical'
}

/**
 * 드래그 가능한 패널 경계선.
 * direction="horizontal" → 좌우 패널 사이 수직 바 (col-resize)
 * direction="vertical"   → 상하 패널 사이 수평 바 (row-resize)
 */
export default function ResizeHandle({ direction = 'horizontal' }: ResizeHandleProps) {
  const isHorizontal = direction === 'horizontal'

  return (
    <PanelResizeHandle
      className="group flex items-center justify-center flex-shrink-0 relative"
      style={{
        width: isHorizontal ? '4px' : '100%',
        height: isHorizontal ? '100%' : '4px',
        cursor: isHorizontal ? 'col-resize' : 'row-resize',
        backgroundColor: 'var(--color-border)',
        transition: 'background-color 0.15s',
      }}
      onDragging={(isDragging) => {
        // 드래그 중에도 커서 유지
        document.body.style.cursor = isDragging
          ? (isHorizontal ? 'col-resize' : 'row-resize')
          : ''
      }}
    >
      {/* 핸들 핀 */}
      <div
        className="absolute rounded-full opacity-0 group-hover:opacity-100 group-data-[resize-handle-active]:opacity-100 transition-opacity"
        style={{
          width: isHorizontal ? '4px' : '32px',
          height: isHorizontal ? '32px' : '4px',
          backgroundColor: 'var(--color-primary)',
        }}
      />
    </PanelResizeHandle>
  )
}
