import { formatINR } from '@/lib/api';

interface Card {
  label: string;
  value: string | number;
  subtitle?: string;
  icon: string;
  color?: string;
}

export default function SummaryCards({ cards }: { cards: Card[] }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
      {cards.map((card, i) => (
        <div key={i} style={{
          background: '#FFFFFF',
          border: '1px solid #E5E7EB',
          borderRadius: 12,
          padding: '20px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
            <span style={{ fontSize: 22 }}>{card.icon}</span>
          </div>
          <div style={{
            fontSize: 26,
            fontWeight: 700,
            color: card.color || '#111827',
            fontFamily: 'JetBrains Mono, monospace',
            lineHeight: 1.2,
          }}>{card.value}</div>
          <div style={{ fontSize: 14, color: '#6B7280', marginTop: 4, fontWeight: 500 }}>{card.label}</div>
          {card.subtitle && (
            <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 2 }}>{card.subtitle}</div>
          )}
        </div>
      ))}
    </div>
  );
}
