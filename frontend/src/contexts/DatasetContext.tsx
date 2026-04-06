import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'

interface DatasetContextValue {
  dataset: string
  setDataset: (dataset: string) => void
}

const DatasetContext = createContext<DatasetContextValue>({
  dataset: 'ontology',
  setDataset: () => {},
})

export function DatasetProvider({ children }: { children: ReactNode }) {
  const [dataset, setDataset] = useState('ontology')
  return (
    <DatasetContext.Provider value={{ dataset, setDataset }}>
      {children}
    </DatasetContext.Provider>
  )
}

export function useDataset(): DatasetContextValue {
  return useContext(DatasetContext)
}
