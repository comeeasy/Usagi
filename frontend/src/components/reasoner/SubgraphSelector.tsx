// TODO: 추론 대상 서브그래프 선택
// Named Graph IRI 목록 체크박스 선택
// "전체 온톨로지" 선택 옵션
// 추론 프로파일 선택 (EL / RL / QL / FULL)

interface SubgraphSelectorProps {
  availableGraphs?: string[]
  selectedGraphs?: string[]
  onSelectionChange?: (graphs: string[]) => void
  profile?: string
  onProfileChange?: (profile: string) => void
}

export default function SubgraphSelector({
  availableGraphs = [],
  selectedGraphs = [],
  onSelectionChange,
  profile = 'EL',
  onProfileChange,
}: SubgraphSelectorProps) {
  return (
    <div className="flex flex-col gap-2">
      {/* TODO: graph selection checkboxes + profile selector */}
    </div>
  )
}
