'use client';

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string | number;
  style?: React.CSSProperties;
}

export function Skeleton({ width = '100%', height = 16, borderRadius = 6, style }: SkeletonProps) {
  return (
    <div style={{
      width,
      height,
      borderRadius,
      background: 'linear-gradient(90deg, var(--surface-2) 25%, rgba(255,255,255,0.04) 50%, var(--surface-2) 75%)',
      backgroundSize: '200% 100%',
      animation: 'shimmer 1.6s infinite',
      ...style,
    }} />
  );
}

export function KPICardSkeleton() {
  return (
    <div className="card" style={{ padding: '22px 24px', borderTop: '2px solid var(--border-2)' }}>
      <Skeleton width={80} height={10} style={{ marginBottom: 14 }} />
      <Skeleton width={120} height={28} style={{ marginBottom: 10 }} />
      <Skeleton width={100} height={12} />
    </div>
  );
}

export function KPIGridSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="kpi-grid-4">
      {Array.from({ length: count }).map((_, i) => <KPICardSkeleton key={i} />)}
    </div>
  );
}

export function TableRowSkeleton({ cols = 6 }: { cols?: number }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i}>
          <Skeleton width={i === 0 ? 80 : i === cols - 1 ? 60 : '90%'} height={13} />
        </td>
      ))}
    </tr>
  );
}

export function TableSkeleton({ rows = 5, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div className="table-scroll-wrapper">
      <table className="data-table">
        <thead>
          <tr>
            {Array.from({ length: cols }).map((_, i) => (
              <th key={i}><Skeleton width={50 + i * 10} height={11} /></th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, i) => (
            <TableRowSkeleton key={i} cols={cols} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ChartSkeleton({ height = 200 }: { height?: number }) {
  return (
    <div style={{ position: 'relative', height, display: 'flex', alignItems: 'flex-end', gap: 6, padding: '0 4px' }}>
      {Array.from({ length: 8 }).map((_, i) => {
        const h = [40, 70, 55, 90, 65, 80, 45, 60][i] ?? 60;
        return (
          <div key={i} style={{ flex: 1, height: `${h}%`, borderRadius: '4px 4px 0 0' }}>
            <Skeleton width="100%" height="100%" borderRadius="4px 4px 0 0" />
          </div>
        );
      })}
    </div>
  );
}
