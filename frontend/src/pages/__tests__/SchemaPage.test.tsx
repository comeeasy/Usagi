import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor, fireEvent, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../tests/mocks/server'
import { mockConcept, mockObjectProperty, mockDataProperty, mockIndividual } from '../../tests/mocks/handlers'
import { renderWithProviders } from '../../tests/utils'
import SchemaPage from '../ontology/SchemaPage'
import { NamedGraphsProvider } from '@/contexts/NamedGraphsContext'

// react-resizable-panels — jsdom에서 동작 안 함, 단순 div로 대체
vi.mock('react-resizable-panels', () => ({
  PanelGroup: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Panel: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  PanelResizeHandle: () => <div data-panel-resize-handle-id="mock" />,
}))

// getConcept — mock so detail panel doesn't need real fetch
vi.mock('@/api/entities', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/entities')>()
  return {
    ...actual,
    getConcept: vi.fn().mockResolvedValue(mockConcept),
  }
})

const ROUTE_PATH = '/:ontologyId/schema'
const INITIAL_ENTRY = '/test-ont-uuid/schema'

function renderSchemaPage() {
  return renderWithProviders(
    <NamedGraphsProvider>
      <SchemaPage />
    </NamedGraphsProvider>,
    {
    initialEntries: [INITIAL_ENTRY],
    path: ROUTE_PATH,
    },
  )
}

/** concepts 섹션 내에서 개념을 클릭 (domain/range span과 중복 방지) */
async function clickConcept() {
  const section = await screen.findByTestId('schema-concepts-section')
  const item = await within(section).findByText(mockConcept.label)
  fireEvent.click(item)
}

/** Properties 서브탭으로 전환 */
async function switchToPropertiesTab() {
  const tab = await screen.findByRole('button', { name: /^Properties$/i })
  fireEvent.click(tab)
}

/** properties 섹션 내에서 property를 클릭 */
async function clickObjectProperty() {
  await switchToPropertiesTab()
  const section = await screen.findByTestId('schema-properties-section')
  const item = await within(section).findByText(mockObjectProperty.label)
  fireEvent.click(item)
}

// ─────────────────────────────────────────────
// 1. 초기 렌더링
// ─────────────────────────────────────────────
describe('SchemaPage — 초기 렌더링', () => {
  it('Concepts 섹션 헤더가 표시된다', async () => {
    renderSchemaPage()
    const section = await screen.findByTestId('schema-concepts-section')
    expect(within(section).getByText(/Concepts/i)).toBeInTheDocument()
  })

  it('Properties 섹션 헤더가 표시된다', async () => {
    renderSchemaPage()
    const section = await screen.findByTestId('schema-properties-section')
    expect(within(section).getByText(/Properties/i)).toBeInTheDocument()
  })

  it('Concept 목록이 로드된다', async () => {
    renderSchemaPage()
    const section = await screen.findByTestId('schema-concepts-section')
    await waitFor(() => {
      expect(within(section).getByText(mockConcept.label)).toBeInTheDocument()
    })
  })

  it('Object Property 목록이 로드된다', async () => {
    renderSchemaPage()
    const section = await screen.findByTestId('schema-properties-section')
    await waitFor(() => {
      expect(within(section).getByText(mockObjectProperty.label)).toBeInTheDocument()
    })
  })

  it('Property 목록에 domain → range 인라인 화살표가 표시된다', async () => {
    renderSchemaPage()
    const section = await screen.findByTestId('schema-properties-section')
    await waitFor(() => {
      expect(within(section).getByText(mockObjectProperty.label)).toBeInTheDocument()
    })
    const arrows = within(section).getAllByText('→')
    expect(arrows.length).toBeGreaterThan(0)
  })

  it('New Concept 버튼이 있다', async () => {
    renderSchemaPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /New Concept/i })).toBeInTheDocument()
    })
  })

  it('New Property 버튼이 있다', async () => {
    renderSchemaPage()
    await switchToPropertiesTab()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /New Property/i })).toBeInTheDocument()
    })
  })

  it('초기 상태에서 우측 Detail 서브탭은 없다', async () => {
    renderSchemaPage()
    // concepts 섹션 로드 대기
    const section = await screen.findByTestId('schema-concepts-section')
    await waitFor(() => within(section).getByText(mockConcept.label))
    // Detail 서브탭이 없어야 함
    expect(screen.queryByRole('button', { name: /^Detail$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Relations$/i })).not.toBeInTheDocument()
  })
})

// ─────────────────────────────────────────────
// 2. Concept 선택
// ─────────────────────────────────────────────
describe('SchemaPage — Concept 선택', () => {
  it('Concept 클릭 시 우측 패널에 Detail 탭이 열린다', async () => {
    renderSchemaPage()
    await clickConcept()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Detail$/i })).toBeInTheDocument()
    })
  })

  it('Concept 선택 시 Relations 탭 버튼이 표시된다', async () => {
    renderSchemaPage()
    await clickConcept()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Relations$/i })).toBeInTheDocument()
    })
  })

  it('Concept 선택 시 Instances 탭 버튼이 없다 (개별 Individuals 패널로 이동됨)', async () => {
    renderSchemaPage()
    await clickConcept()
    // Instances 탭이 개념 detail 패널에서 제거됨
    await waitFor(() => screen.getByRole('button', { name: /^Detail$/i }))
    expect(screen.queryByRole('button', { name: /^Instances$/i })).not.toBeInTheDocument()
  })

})

// ─────────────────────────────────────────────
// 3. Concept — Relations 탭
// ─────────────────────────────────────────────
describe('SchemaPage — Concept Relations 탭', () => {
  it('Relations 탭 클릭 시 "as domain" 섹션이 있다', async () => {
    renderSchemaPage()
    await clickConcept()
    await waitFor(() => screen.getByRole('button', { name: /^Relations$/i }))
    fireEvent.click(screen.getByRole('button', { name: /^Relations$/i }))
    await waitFor(() => {
      expect(screen.getByText(/as domain/i)).toBeInTheDocument()
    })
  })

  it('Relations 탭 클릭 시 "as range" 섹션이 있다', async () => {
    renderSchemaPage()
    await clickConcept()
    await waitFor(() => screen.getByRole('button', { name: /^Relations$/i }))
    fireEvent.click(screen.getByRole('button', { name: /^Relations$/i }))
    await waitFor(() => {
      expect(screen.getByText(/as range/i)).toBeInTheDocument()
    })
  })

  it('Relations 탭 클릭 시 domain으로 사용된 Property가 표시된다', async () => {
    renderSchemaPage()
    await clickConcept()
    await waitFor(() => screen.getByRole('button', { name: /^Relations$/i }))
    fireEvent.click(screen.getByRole('button', { name: /^Relations$/i }))
    await waitFor(() => {
      expect(screen.getAllByText(mockObjectProperty.label).length).toBeGreaterThan(0)
    })
  })
})


// ─────────────────────────────────────────────
// 5. Property 선택
// ─────────────────────────────────────────────
describe('SchemaPage — Property 선택', () => {
  it('Property 클릭 시 우측 패널에 type 배지가 표시된다', async () => {
    renderSchemaPage()
    await clickObjectProperty()
    await waitFor(() => {
      expect(screen.getByText(/Object Property/i)).toBeInTheDocument()
    })
  })

  it('Property 클릭 시 Domain 레이블이 표시된다', async () => {
    renderSchemaPage()
    await clickObjectProperty()
    await waitFor(() => {
      const labels = screen.getAllByText(/^Domain$/i)
      expect(labels.length).toBeGreaterThan(0)
    })
  })

  it('Property 클릭 시 Range 레이블이 표시된다', async () => {
    renderSchemaPage()
    await clickObjectProperty()
    await waitFor(() => {
      const labels = screen.getAllByText(/^Range$/i)
      expect(labels.length).toBeGreaterThan(0)
    })
  })

  it('Data Property 필터 적용 시 data property가 표시된다', async () => {
    renderSchemaPage()
    await switchToPropertiesTab()
    await waitFor(() => screen.getByRole('button', { name: /^Data$/i }))
    fireEvent.click(screen.getByRole('button', { name: /^Data$/i }))
    const section = await screen.findByTestId('schema-properties-section')
    await waitFor(() => {
      expect(within(section).getByText(mockDataProperty.label)).toBeInTheDocument()
    })
  })
})

// ─────────────────────────────────────────────
// 6. Property Domain 클릭 → Concept 포커스
// ─────────────────────────────────────────────
describe('SchemaPage — Property Domain 클릭', () => {
  it('Property detail의 Domain 배지 클릭 시 Concept Detail 탭으로 전환된다', async () => {
    renderSchemaPage()
    await clickObjectProperty()

    // "Domain" label이 포함된 섹션 안의 button을 클릭
    await waitFor(() => screen.getAllByText(/^Domain$/i))
    const domainLabel = screen.getAllByText(/^Domain$/i)[0]
    const domainSection = domainLabel.closest('div')!
    const domainBadge = domainSection.querySelector('button')

    if (domainBadge) {
      fireEvent.click(domainBadge)
      await waitFor(() => {
        // Concept 뷰로 전환 → Detail/Relations 서브탭 출현
        expect(screen.getByRole('button', { name: /^Detail$/i })).toBeInTheDocument()
      })
    }
  })
})

// ─────────────────────────────────────────────
// 7. 폼 생성
// ─────────────────────────────────────────────
describe('SchemaPage — 생성 폼', () => {
  it('New Concept 클릭 시 Concept 생성 폼이 열린다', async () => {
    renderSchemaPage()
    await waitFor(() => screen.getByRole('button', { name: /New Concept/i }))
    fireEvent.click(screen.getByRole('button', { name: /New Concept/i }))
    await waitFor(() => {
      expect(screen.getByText(/Create Concept/i)).toBeInTheDocument()
    })
  })

  it('New Property 클릭 시 Property 생성 폼이 열린다', async () => {
    renderSchemaPage()
    await switchToPropertiesTab()
    await waitFor(() => screen.getByRole('button', { name: /New Property/i }))
    fireEvent.click(screen.getByRole('button', { name: /New Property/i }))
    await waitFor(() => {
      expect(screen.getByText(/Create Property/i)).toBeInTheDocument()
    })
  })
})

// ─────────────────────────────────────────────
// 8. 빈 상태
// ─────────────────────────────────────────────
describe('SchemaPage — 빈 상태', () => {
  it('Concept이 없으면 concept 섹션에 empty 메시지가 표시된다', async () => {
    server.use(
      http.get('/api/v1/ontologies/:id/concepts', () =>
        HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20 }),
      ),
    )
    renderSchemaPage()
    const section = await screen.findByTestId('schema-concepts-section')
    await waitFor(() => {
      expect(within(section).getByText(/No concepts/i)).toBeInTheDocument()
    })
  })

  it('Property가 없으면 property 섹션에 empty 메시지가 표시된다', async () => {
    server.use(
      http.get('/api/v1/ontologies/:id/properties', () =>
        HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20 }),
      ),
    )
    renderSchemaPage()
    const section = await screen.findByTestId('schema-properties-section')
    await waitFor(() => {
      expect(within(section).getByText(/No properties/i)).toBeInTheDocument()
    })
  })
})

// ─────────────────────────────────────────────
// 9. Resizable Panels
// ─────────────────────────────────────────────
describe('SchemaPage — Resizable Panels', () => {
  it('ResizeHandle이 렌더된다', async () => {
    renderSchemaPage()
    await waitFor(() => {
      const handles = document.querySelectorAll('[data-panel-resize-handle-id]')
      expect(handles.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('Concepts / Properties / Individuals 섹션이 렌더된다', async () => {
    renderSchemaPage()
    await waitFor(() => {
      expect(screen.getByTestId('schema-concepts-section')).toBeInTheDocument()
      expect(screen.getByTestId('schema-properties-section')).toBeInTheDocument()
      expect(screen.getByTestId('schema-individuals-section')).toBeInTheDocument()
    })
  })
})

// ─────────────────────────────────────────────
// 10. Individuals 탭
// ─────────────────────────────────────────────

/** Individuals 서브탭으로 전환 */
async function switchToIndividualsTab() {
  const tab = await screen.findByRole('button', { name: /^Individuals$/i })
  fireEvent.click(tab)
}

describe('SchemaPage — Individuals 탭', () => {
  it('Individuals 서브탭 버튼이 표시된다', async () => {
    renderSchemaPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Individuals$/i })).toBeInTheDocument()
    })
  })

  it('Individuals 탭 클릭 시 Individual 목록이 로드된다', async () => {
    renderSchemaPage()
    await switchToIndividualsTab()
    const section = await screen.findByTestId('schema-individuals-section')
    await waitFor(() => {
      expect(within(section).getByText(mockIndividual.label!)).toBeInTheDocument()
    })
  })

  it('New Individual 버튼이 있다', async () => {
    renderSchemaPage()
    await switchToIndividualsTab()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /New Individual/i })).toBeInTheDocument()
    })
  })

  it('Individual 클릭 시 우측 패널에 Individual 상세가 표시된다', async () => {
    renderSchemaPage()
    await switchToIndividualsTab()
    const section = await screen.findByTestId('schema-individuals-section')
    const item = await within(section).findByText(mockIndividual.label!)
    fireEvent.click(item)
    await waitFor(() => {
      expect(screen.getByTestId('schema-individual-detail-panel')).toBeInTheDocument()
    })
  })

  it('New Individual 클릭 시 Individual 생성 폼이 열린다', async () => {
    renderSchemaPage()
    await switchToIndividualsTab()
    await waitFor(() => screen.getByRole('button', { name: /New Individual/i }))
    fireEvent.click(screen.getByRole('button', { name: /New Individual/i }))
    await waitFor(() => {
      expect(screen.getByText(/Create Individual/i)).toBeInTheDocument()
    })
  })

  it('Individual이 없으면 empty 메시지가 표시된다', async () => {
    server.use(
      http.get('/api/v1/ontologies/:id/individuals', () =>
        HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20 }),
      ),
    )
    renderSchemaPage()
    await switchToIndividualsTab()
    const section = await screen.findByTestId('schema-individuals-section')
    await waitFor(() => {
      expect(within(section).getByText(/No individuals/i)).toBeInTheDocument()
    })
  })
})

// ─────────────────────────────────────────────
// 11. Concept Detail — 완전한 필드 표시
// ─────────────────────────────────────────────
describe('SchemaPage — Concept Detail 완전성', () => {
  it('Concept Detail 탭에 Instances 레이블이 표시된다', async () => {
    renderSchemaPage()
    await clickConcept()
    await waitFor(() => screen.getByRole('button', { name: /^Detail$/i }))
    await waitFor(() => {
      expect(screen.getByText(/^Instances$/i)).toBeInTheDocument()
    })
  })

  it('Concept Detail 탭에 Subclasses 레이블이 표시된다', async () => {
    renderSchemaPage()
    await clickConcept()
    await waitFor(() => screen.getByRole('button', { name: /^Detail$/i }))
    await waitFor(() => {
      expect(screen.getByText(/^Subclasses$/i)).toBeInTheDocument()
    })
  })

  it('Concept Detail 탭에 Parent Class IRI가 표시된다', async () => {
    renderSchemaPage()
    await clickConcept()
    await waitFor(() => screen.getByRole('button', { name: /^Detail$/i }))
    await waitFor(() => {
      // super_classes[0]의 localName이 표시되어야 함
      expect(screen.getByText(/Agent/i)).toBeInTheDocument()
    })
  })

  it('Concept에 Provenance 탭 버튼이 표시된다', async () => {
    renderSchemaPage()
    await clickConcept()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Provenance$/i })).toBeInTheDocument()
    })
  })
})

// ─────────────────────────────────────────────
// 12. Property Detail — 완전한 필드 표시
// ─────────────────────────────────────────────
describe('SchemaPage — Property Detail 완전성', () => {
  it('Property에 Provenance 탭 버튼이 표시된다', async () => {
    renderSchemaPage()
    await clickObjectProperty()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Provenance$/i })).toBeInTheDocument()
    })
  })

  it('Object Property Detail에 Characteristics가 표시된다', async () => {
    renderSchemaPage()
    await clickObjectProperty()
    await waitFor(() => {
      expect(screen.getByText(/Asymmetric/i)).toBeInTheDocument()
    })
  })

  it('Object Property Detail에 InverseOf가 표시된다', async () => {
    renderSchemaPage()
    await clickObjectProperty()
    await waitFor(() => {
      expect(screen.getByText(/hasChild/i)).toBeInTheDocument()
    })
  })

  it('Object Property Detail에 Super Properties가 표시된다', async () => {
    renderSchemaPage()
    await clickObjectProperty()
    await waitFor(() => {
      expect(screen.getByText(/hasAncestor/i)).toBeInTheDocument()
    })
  })

  it('Data Property Detail에 isFunctional이 표시된다', async () => {
    renderSchemaPage()
    await switchToPropertiesTab()
    await waitFor(() => screen.getByRole('button', { name: /^Data$/i }))
    fireEvent.click(screen.getByRole('button', { name: /^Data$/i }))
    const section = await screen.findByTestId('schema-properties-section')
    const item = await within(section).findByText(mockDataProperty.label)
    fireEvent.click(item)
    await waitFor(() => {
      // Functional 레이블과 값 배지 모두 존재 확인
      const matches = screen.getAllByText(/functional/i)
      expect(matches.length).toBeGreaterThanOrEqual(1)
    })
  })
})

// ─────────────────────────────────────────────
// 13. Individual Detail — 완전한 필드 표시
// ─────────────────────────────────────────────
describe('SchemaPage — Individual Detail 완전성', () => {
  it('Individual Detail에 Object Property value가 표시된다', async () => {
    renderSchemaPage()
    await switchToIndividualsTab()
    const section = await screen.findByTestId('schema-individuals-section')
    const item = await within(section).findByText(mockIndividual.label!)
    fireEvent.click(item)
    await waitFor(() => {
      // object_property_values[0].property_iri의 localName
      expect(screen.getByText(/hasParent/i)).toBeInTheDocument()
    })
  })

  it('Individual에 Provenance 탭 버튼이 표시된다', async () => {
    renderSchemaPage()
    await switchToIndividualsTab()
    const section = await screen.findByTestId('schema-individuals-section')
    const item = await within(section).findByText(mockIndividual.label!)
    fireEvent.click(item)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Provenance$/i })).toBeInTheDocument()
    })
  })

  it('Individual Provenance 탭에 provenance 레코드가 표시된다', async () => {
    renderSchemaPage()
    await switchToIndividualsTab()
    const section = await screen.findByTestId('schema-individuals-section')
    const item = await within(section).findByText(mockIndividual.label!)
    fireEvent.click(item)
    await waitFor(() => screen.getByRole('button', { name: /^Provenance$/i }))
    fireEvent.click(screen.getByRole('button', { name: /^Provenance$/i }))
    await waitFor(() => {
      expect(screen.getByText(/test-source-1/i)).toBeInTheDocument()
    })
  })
})
