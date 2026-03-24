import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertTriangle } from 'lucide-react'

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
}

export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback

      return (
        <div
          className="flex flex-col items-center justify-center p-8 rounded-lg border gap-3"
          style={{
            borderColor: 'var(--color-error)',
            backgroundColor: 'var(--color-bg-surface)',
          }}
        >
          <AlertTriangle size={32} style={{ color: 'var(--color-error)' }} />
          <div className="text-center">
            <p className="font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              Something went wrong
            </p>
            {this.state.error && (
              <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                {this.state.error.message}
              </p>
            )}
          </div>
          <button
            className="px-4 py-1.5 text-sm rounded transition-opacity hover:opacity-80"
            style={{
              backgroundColor: 'var(--color-bg-elevated)',
              color: 'var(--color-text-primary)',
              border: '1px solid var(--color-border)',
            }}
            onClick={() => this.setState({ hasError: false })}
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
