/** Identical analysis-window shell for gait and single-transition tasks. */
export default function AnalysisWindowPanel({ title, expanded, onToggle, description, children }) {
  return <div className="mb-6 rounded-lg border border-zinc-600 bg-zinc-700">
    <button type="button" className="w-full px-4 py-2 text-left font-semibold" aria-expanded={expanded} onClick={onToggle}>{expanded ? '▾' : '▸'} {title}</button>
    {expanded && <div className="border-t border-zinc-600 p-3">
      {description && <div className="mb-2 text-xs">{description}</div>}
      {children}
    </div>}
  </div>;
}
