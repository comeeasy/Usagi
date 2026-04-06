import { useEffect, useState } from 'react'
import { Database } from 'lucide-react'
import { useDataset } from '@/contexts/DatasetContext'
import { listDatasets } from '@/api/ontologies'
import type { DatasetInfo } from '@/api/ontologies'

export default function DatasetSelector() {
  const { dataset, setDataset } = useDataset()
  const [datasets, setDatasets] = useState<DatasetInfo[]>([])

  useEffect(() => {
    listDatasets()
      .then(setDatasets)
      .catch(() => {
        // Fuseki admin API 접근 불가 시 현재 dataset 그대로 유지
        setDatasets([{ name: dataset, type: 'active' }])
      })
  }, [dataset])

  return (
    <div className="px-3 py-2 border-b" style={{ borderColor: 'var(--color-border)' }}>
      <label className="text-xs mb-1 flex items-center gap-1" style={{ color: 'var(--color-text-muted)' }}>
        <Database size={11} />
        Dataset
      </label>
      <select
        className="w-full text-xs px-2 py-1.5 rounded border"
        style={{
          backgroundColor: 'var(--color-bg-elevated)',
          borderColor: 'var(--color-border)',
          color: 'var(--color-text-primary)',
        }}
        value={dataset}
        onChange={(e) => setDataset(e.target.value)}
      >
        {datasets.map((ds) => (
          <option key={ds.name} value={ds.name}>
            {ds.name}
          </option>
        ))}
      </select>
    </div>
  )
}
