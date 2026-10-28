import { useQuery } from '@tanstack/react-query'
import { healthApi } from '@/services/api'
import { cn, severityDot } from '@/lib/utils'

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </svg>
  )
}

function RefreshIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
      <path d="M21 3v5h-5" />
      <path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
      <path d="M3 21v-5h5" />
    </svg>
  )
}

function BellIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </svg>
  )
}

function SunIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  )
}

export default function TopBar() {
  const { data } = useQuery({
    queryKey: ['health'],
    queryFn: healthApi.check,
    refetchInterval: 30_000,
    retry: false,
  })
  const monitoring = data?.database?.status === 'connected' ? 'Monitoring Active' : 'Connecting…'
  const ok = data?.database?.status === 'connected' || !data

  return (
    <header className="flex items-center gap-4 px-6 py-3 border-b border-border bg-background/80 backdrop-blur sticky top-0 z-20">
      <div className="relative flex-1 max-w-2xl">
        <SearchIcon className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-subtle" />
        <input
          className="input pl-9 pr-4"
          placeholder="Search features, incidents, pipelines…"
        />
      </div>

      <div
        className={cn(
          'hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-medium',
          ok
            ? 'bg-severity-healthy/10 border-severity-healthy/30 text-severity-healthy'
            : 'bg-severity-medium/10 border-severity-medium/30 text-severity-medium',
        )}
      >
        <span className={cn('w-2 h-2 rounded-full animate-pulse', severityDot(ok ? 'Healthy' : 'Warning'))} />
        {monitoring}
      </div>

      <div className="flex items-center gap-1">
        <button className="p-2 rounded-md hover:bg-surface-2 text-text-muted" title="Refresh">
          <RefreshIcon className="w-[18px] h-[18px]" />
        </button>
        <button className="relative p-2 rounded-md hover:bg-surface-2 text-text-muted" title="Notifications">
          <BellIcon className="w-[18px] h-[18px]" />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-severity-critical" />
        </button>
        <button className="p-2 rounded-md hover:bg-surface-2 text-text-muted" title="Theme">
          <SunIcon className="w-[18px] h-[18px]" />
        </button>
      </div>
    </header>
  )
}
