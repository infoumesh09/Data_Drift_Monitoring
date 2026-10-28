import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'

type IconProps = { className?: string }

const Icon = {
  Overview: ({ className }: IconProps) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="16" width="7" height="5" rx="1.5" />
    </svg>
  ),
  Pipeline: ({ className }: IconProps) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 7h3a2 2 0 0 1 2 2v6a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-2" />
      <circle cx="4" cy="7" r="1.4" />
      <circle cx="20" cy="11" r="1.4" />
      <path d="M10 9v6M14 9v6" />
    </svg>
  ),
  Trend: ({ className }: IconProps) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 17l6-6 4 4 8-8" />
      <path d="M14 7h7v7" />
    </svg>
  ),
  Schema: ({ className }: IconProps) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="5" rx="8" ry="2.5" />
      <path d="M4 5v6c0 1.4 3.6 2.5 8 2.5s8-1.1 8-2.5V5" />
      <path d="M4 11v6c0 1.4 3.6 2.5 8 2.5s8-1.1 8-2.5v-6" />
    </svg>
  ),
  Alert: ({ className }: IconProps) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.3 3.72 2.52 16.83a2 2 0 0 0 1.72 3h15.52a2 2 0 0 0 1.72-3L13.71 3.72a2 2 0 0 0-3.41 0Z" />
      <path d="M12 9v4M12 17h.01" />
    </svg>
  ),
  Brain: ({ className }: IconProps) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.5 2a2.5 2.5 0 0 1 2.5 2.5V20a2.5 2.5 0 1 1-5 0V7a2 2 0 0 0-2-2 2.5 2.5 0 0 1 0-5h3.5a2.5 2.5 0 0 1 1.5-.5Z" />
      <path d="M14.5 2a2.5 2.5 0 0 0-2.5 2.5V20a2.5 2.5 0 1 0 5 0V7a2 2 0 0 1 2-2 2.5 2.5 0 0 0 0-5h-3.5A2.5 2.5 0 0 0 14.5 2Z" />
    </svg>
  ),
  BarChart: ({ className }: IconProps) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <rect x="7" y="12" width="3" height="6" rx="0.5" />
      <rect x="12" y="8" width="3" height="10" rx="0.5" />
      <rect x="17" y="4" width="3" height="14" rx="0.5" />
    </svg>
  ),
  Flask: ({ className }: IconProps) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 3h6M10 3v6L4.5 18a2 2 0 0 0 1.7 3h11.6a2 2 0 0 0 1.7-3L14 9V3" />
      <path d="M7.5 15h9" />
    </svg>
  ),
  Dataset: ({ className }: IconProps) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 10h18M9 4v16" />
    </svg>
  ),
  Settings: ({ className }: IconProps) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1A1.7 1.7 0 0 0 9 19.4a1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1A1.7 1.7 0 0 0 4.6 9 1.7 1.7 0 0 0 4.3 7.2l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1A1.7 1.7 0 0 0 15 4.6a1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z" />
    </svg>
  ),
  ChevronLeft: ({ className }: IconProps) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m15 18-6-6 6-6" />
    </svg>
  ),
  Logo: ({ className }: IconProps) => (
    <svg className={className} viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="8" fill="url(#g)" />
      <path d="M9 20V12a3 3 0 0 1 5.4-1.8M23 12v8a3 3 0 0 1-5.4 1.8" stroke="white" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="16" cy="16" r="1.8" fill="white" />
      <defs>
        <linearGradient id="g" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop stopColor="#3b82f6" />
          <stop offset="1" stopColor="#6366f1" />
        </linearGradient>
      </defs>
    </svg>
  ),
}

const NAV = [
  {
    group: 'MONITORING',
    items: [
      { to: '/overview', label: 'Overview', Icon: Icon.Overview, badge: null },
      { to: '/pipelines', label: 'Pipelines', Icon: Icon.Pipeline, badge: null },
      { to: '/drift-monitoring', label: 'Drift Monitoring', Icon: Icon.Trend, badge: null },
      { to: '/schema-monitoring', label: 'Schema Monitoring', Icon: Icon.Schema, badge: null },
      { to: '/incidents', label: 'Incidents', Icon: Icon.Alert, badge: '3' },
    ],
  },
  {
    group: 'ANALYSIS',
    items: [
      { to: '/ai-diagnosis', label: 'AI Diagnosis', Icon: Icon.Brain, badge: null },
      { to: '/algorithm-comparison', label: 'Algorithm Comparison', Icon: Icon.BarChart, badge: null },
      { to: '/experiments', label: 'Experiments', Icon: Icon.Flask, badge: null },
    ],
  },
  {
    group: 'DATA',
    items: [
      { to: '/datasets', label: 'Datasets', Icon: Icon.Dataset, badge: null },
      { to: '/settings', label: 'Settings', Icon: Icon.Settings, badge: null },
    ],
  },
]

export default function Sidebar() {
  return (
    <aside className="flex flex-col w-72 shrink-0 h-full bg-background border-r border-border">
      <div className="flex items-center gap-3 px-4 py-4 border-b border-border">
        <Icon.Logo className="w-10 h-10 shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-white text-[15px] leading-tight">DriftSense</div>
          <div className="text-xs text-text-muted">AI Data Observability</div>
        </div>
        <button className="p-1.5 rounded-md hover:bg-surface-2 text-text-muted">
          <Icon.ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        {NAV.map((section) => (
          <div key={section.group}>
            <div className="section-title px-3 mb-2">{section.group}</div>
            <ul className="space-y-1">
              {section.items.map(({ to, label, Icon, badge }) => (
                <li key={to}>
                  <NavLink
                    to={to}
                    className={({ isActive }) =>
                      cn('nav-item group relative', isActive && 'nav-item-active')
                    }
                  >
                    <Icon className="w-[18px] h-[18px] shrink-0 opacity-90" />
                    <span className="flex-1">{label}</span>
                    {badge && (
                      <span className="text-[10px] font-bold bg-severity-critical text-white rounded-full w-5 h-5 flex items-center justify-center">
                        {badge}
                      </span>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="p-3 border-t border-border">
        <div className="flex items-center gap-3 p-2 rounded-lg bg-surface hover:bg-surface-2 transition-colors cursor-pointer">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-indigo-500 text-white flex items-center justify-center text-sm font-semibold">
            DA
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-white truncate">Demo Admin</div>
            <div className="text-xs text-text-muted truncate">Final Year Project</div>
          </div>
        </div>
      </div>
    </aside>
  )
}
