const styles = {
  good: 'border-emerald-500 bg-emerald-950 text-emerald-200',
  review: 'border-amber-500 bg-amber-950 text-amber-200',
  failed: 'border-red-500 bg-red-950 text-red-200',
};

export default function AnalysisQualityBadge({ quality }) {
  if (!quality) return null;
  const status = quality.status || 'review';
  const explanation = [
    quality.disclaimer,
    ...(quality.reasons || []),
  ].filter(Boolean).join('\n');
  return (
    <span
      className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${styles[status] || styles.review}`}
      title={explanation}
      aria-label={`Analysis quality: ${quality.label || status}`}
    >
      Quality: {quality.label || status}
    </span>
  );
}
