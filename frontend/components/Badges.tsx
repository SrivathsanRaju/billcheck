const SEV: Record<string, { bg: string; color: string }> = {
  critical: { bg: 'rgba(255,71,87,0.15)',   color: '#FF4757' },
  high:     { bg: 'rgba(255,181,71,0.15)',  color: '#FFB547' },
  medium:   { bg: 'rgba(78,142,255,0.15)',  color: '#4E8EFF' },
  low:      { bg: 'rgba(0,196,140,0.15)',   color: '#00C48C' },
};
const STA: Record<string, { bg: string; color: string }> = {
  completed:    { bg: 'rgba(0,196,140,0.15)',   color: '#00C48C' },
  processing:   { bg: 'rgba(78,142,255,0.15)',  color: '#4E8EFF' },
  pending:      { bg: 'rgba(255,181,71,0.15)',  color: '#FFB547' },
  failed:       { bg: 'rgba(255,71,87,0.15)',   color: '#FF4757' },
  raised:       { bg: 'rgba(123,92,196,0.15)',  color: '#7B5CC4' },
  acknowledged: { bg: 'rgba(255,181,71,0.15)',  color: '#FFB547' },
  resolved:     { bg: 'rgba(0,196,140,0.15)',   color: '#00C48C' },
  rejected:     { bg: 'rgba(139,147,184,0.15)', color: '#8B93B8' },
};

export function SeverityBadge({ severity }: { severity: string }) {
  const s = SEV[severity] || STA.rejected;
  return (
    <span className="badge" style={{ background: s.bg, color: s.color }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: s.color, display: 'inline-block', flexShrink: 0 }}/>
      {severity}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const s = STA[status] || STA.rejected;
  return (
    <span className="badge" style={{ background: s.bg, color: s.color, textTransform: 'capitalize' }}>
      {status}
    </span>
  );
}
