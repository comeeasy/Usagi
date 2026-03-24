interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizeClasses = {
  sm: 'w-4 h-4 border-2',
  md: 'w-6 h-6 border-2',
  lg: 'w-10 h-10 border-4',
}

export default function LoadingSpinner({ size = 'md', className = '' }: LoadingSpinnerProps) {
  return (
    <div
      className={`${sizeClasses[size]} animate-spin rounded-full border-t-transparent ${className}`}
      style={{ borderColor: 'var(--color-primary)', borderTopColor: 'transparent' }}
      role="status"
      aria-label="Loading"
    />
  )
}
