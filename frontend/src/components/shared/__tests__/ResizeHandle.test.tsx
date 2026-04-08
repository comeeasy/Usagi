import { describe, it, expect } from 'vitest'
import * as panels from 'react-resizable-panels'

describe('react-resizable-panels v2 API', () => {
  it('PanelGroup을 export한다', () => {
    expect((panels as Record<string, unknown>).PanelGroup).toBeDefined()
  })

  it('Panel을 export한다', () => {
    expect((panels as Record<string, unknown>).Panel).toBeDefined()
  })

  it('PanelResizeHandle을 export한다', () => {
    expect((panels as Record<string, unknown>).PanelResizeHandle).toBeDefined()
  })

  it('v4 전용 Group export가 없다', () => {
    expect((panels as Record<string, unknown>).Group).toBeUndefined()
  })

  it('v4 전용 Separator export가 없다', () => {
    expect((panels as Record<string, unknown>).Separator).toBeUndefined()
  })
})
