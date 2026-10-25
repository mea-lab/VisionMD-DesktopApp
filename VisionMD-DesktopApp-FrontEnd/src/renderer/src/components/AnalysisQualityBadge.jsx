import { useState } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button } from '@mui/material';
import { useTheme } from '../contexts/ThemeContext';

const colors = { good: '#19733b', review: '#8a5700', failed: '#b82020' };
const display = value => typeof value === 'object'
  ? JSON.stringify(value, null, 2) : String(value ?? 'Not recorded');

export default function AnalysisQualityBadge({ quality }) {
  const [open, setOpen] = useState(false);
  const { theme } = useTheme();
  if (!quality) return null;
  const status = quality.status || 'review';
  const checks = quality.checks || [];
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}
        className="rounded-full border px-2.5 py-1 text-xs font-semibold"
        style={{ backgroundColor: colors[status] || colors.review, color: '#fff' }}
        title="Show quality measurements and decision rules" aria-haspopup="dialog">
        Quality: {quality.label || status}
      </button>
      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="md" fullWidth
        aria-labelledby="analysis-quality-title"
        PaperProps={{ sx: { bgcolor: theme === 'light' ? '#fff' : '#303136',
          color: theme === 'light' ? '#172033' : '#f3f4f6' } }}>
        <DialogTitle id="analysis-quality-title">Estimated quality: {quality.label || status}</DialogTitle>
        <DialogContent dividers>
          <p>{quality.disclaimer || 'Automated technical screening, not clinical validation.'}</p>
          <h3 className="mt-4 font-semibold">Why this result?</h3>
          {quality.reasons?.length
            ? <ul className="list-disc pl-5">{quality.reasons.map((reason, i) => <li key={i}>{reason}</li>)}</ul>
            : <p>No warnings were recorded by the technical checks. This does not guarantee a correct result.</p>}
          {quality.decision_rule && <p className="mt-3">{quality.decision_rule}</p>}
          {quality.signal_selection && <p className="mt-3">Signal checked: {quality.signal_selection}</p>}
          <h3 className="mt-4 font-semibold">Measurements and rules</h3>
          {checks.length ? checks.map((check, i) => (
            <section key={i} className="my-3 rounded border border-gray-500 p-3">
              <h4 className="font-semibold">{check.name} — {check.outcome}</h4>
              <p>{check.rule}</p>
              <pre className="mt-2 whitespace-pre-wrap break-words text-sm">{display(check.observed)}</pre>
            </section>
          )) : (
            <>
              <p>This saved result predates detailed evidence recording. Its original measurements and reasons
                are shown below; unrecorded thresholds cannot be reconstructed here.</p>
              <pre className="mt-2 whitespace-pre-wrap break-words text-sm">{display(quality.metrics || {})}</pre>
            </>
          )}
          {checks.length > 0 && <details className="mt-4">
            <summary>All recorded quality measurements</summary>
            <pre className="mt-2 whitespace-pre-wrap break-words text-sm">{display(quality.metrics || {})}</pre>
          </details>}
          <p className="mt-4 text-sm">Quality algorithm: {quality.version || 'Not recorded'}</p>
        </DialogContent>
        <DialogActions><Button onClick={() => setOpen(false)}>Close</Button></DialogActions>
      </Dialog>
    </>
  );
}
