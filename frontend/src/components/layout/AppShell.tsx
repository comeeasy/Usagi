// TODO: 사이드바 + 메인 콘텐츠 레이아웃
// Sidebar (좌측 고정) + TopBar (상단) + 메인 콘텐츠 영역 (스크롤)

import type { ReactNode } from 'react'

interface AppShellProps {
  children: ReactNode
}

export default function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex h-screen bg-bg-base">
      {/* TODO: <Sidebar /> */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* TODO: <TopBar /> */}
        <main className="flex-1 overflow-auto p-4">
          {children}
        </main>
      </div>
    </div>
  )
}
