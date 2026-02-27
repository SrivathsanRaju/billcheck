'use client';
import { downloadCSV, getDisputeLetter } from '@/lib/api';
import toast from 'react-hot-toast';

const DL = () => <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>;

export default function DownloadButtons({ batchId }: { batchId: number }) {
  const dl = async (type: string, filename: string) => {
    try {
      const r = await downloadCSV(batchId, type);
      const url = URL.createObjectURL(new Blob([r.data]));
      const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error('Download failed'); }
  };
  const dlLetter = async () => {
    try {
      const r = await getDisputeLetter(batchId);
      const url = URL.createObjectURL(new Blob([r.data], { type: 'text/plain' }));
      const a = document.createElement('a'); a.href = url; a.download = `dispute_letter_${batchId}.txt`; a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error('Download failed'); }
  };
  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
      <button className="btn btn-secondary btn-sm" onClick={() => dl('discrepancy', `discrepancies_${batchId}.csv`)}><DL /> Discrepancies</button>
      <button className="btn btn-secondary btn-sm" onClick={() => dl('summary', `summary_${batchId}.csv`)}><DL /> Summary</button>
      <button className="btn btn-secondary btn-sm" onClick={() => dl('payout', `payout_${batchId}.csv`)}><DL /> Payout</button>
      <button className="btn btn-primary btn-sm" onClick={dlLetter}>
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        Dispute Letter
      </button>
    </div>
  );
}
