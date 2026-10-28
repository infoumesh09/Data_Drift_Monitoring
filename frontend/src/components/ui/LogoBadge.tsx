export function LogoBadge({ size = 40 }: { size?: number }) {
  const iconSize = size * 0.55
  return (
    <div
      className="shrink-0 rounded-xl bg-gradient-to-br from-brand-500 to-accent-indigo text-white flex items-center justify-center shadow-glow"
      style={{ width: size, height: size }}
    >
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
      </svg>
    </div>
  )
}

