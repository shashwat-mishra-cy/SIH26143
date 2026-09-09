import { useRef, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

interface DraggablePanelProps {
  children: ReactNode
  initialWidth?: number
  minWidth?: number
  maxWidth?: number
}

/**
 * Lightweight draggable/resizable panel component.
 * Users can drag the left edge to resize horizontally.
 * Respects min/max width constraints.
 */
export default function DraggablePanel({
  children,
  initialWidth = 360,
  minWidth = 320,
  maxWidth = 600,
}: DraggablePanelProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(initialWidth)
  const [isDragging, setIsDragging] = useState(false)

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging || !panelRef.current) return

      const parentRect = panelRef.current.parentElement?.getBoundingClientRect()
      if (!parentRect) return

      // Calculate new width: from right edge of parent to current mouse position
      const newWidth = parentRect.right - e.clientX
      const constrainedWidth = Math.max(minWidth, Math.min(maxWidth, newWidth))

      setWidth(constrainedWidth)
    }

    const handleMouseUp = () => {
      setIsDragging(false)
    }

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'auto'
      document.body.style.userSelect = 'auto'
    }
  }, [isDragging, minWidth, maxWidth])

  return (
    <div
      ref={panelRef}
      className="draggable-panel"
      style={{
        width: `${width}px`,
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}
    >
      {/* Drag handle at left edge */}
      <div
        className="panel-drag-handle"
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          bottom: 0,
          width: '8px',
          cursor: isDragging ? 'col-resize' : 'col-resize',
          background: isDragging ? 'rgba(77, 163, 255, 0.3)' : 'transparent',
          transition: 'background 0.2s ease',
          zIndex: 10,
        }}
        onMouseDown={(e) => {
          setIsDragging(true)
          e.preventDefault()
        }}
      />
      {children}
    </div>
  )
}
