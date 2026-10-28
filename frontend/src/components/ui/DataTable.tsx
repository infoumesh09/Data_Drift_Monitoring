import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export function DataTable({
  headers,
  rows,
  className,
}: {
  headers: { key: string; label: string; className?: string }[];
  rows: { cells: (string | number | ReactNode)[]; className?: string; onClick?: () => void }[];
  className?: string;
}) {
  return (
    <div className={cn('w-full overflow-x-auto', className)}>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-text-dim text-[11px] uppercase tracking-widest font-semibold border-b border-bg-border">
            {headers.map((h) => (
              <th key={h.key} className={cn('text-left px-4 py-3 font-semibold whitespace-nowrap', h.className)}>
                {h.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              onClick={row.onClick}
              className={cn(
                'border-b border-bg-border/60 last:border-b-0 transition-colors',
                row.onClick && 'hover:bg-white/[0.03] cursor-pointer',
                row.className,
              )}
            >
              {row.cells.map((c, j) => (
                <td key={j} className="px-4 py-3 align-middle">
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
