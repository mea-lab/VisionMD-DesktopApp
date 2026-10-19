import { useEffect, useRef, useState } from 'react';

const EVENTS = [
  ['preparation_start', 'Preparation onset', '#c084fc'],
  ['rise_start', 'Upward-ascent onset', '#fb923c'],
  ['rise_end', 'Pelvic movement end', '#4ade80'],
];
const BLUE = '#60a5fa';
const ORANGE = '#fb923c';
const inputClass = 'w-24 rounded border border-zinc-500 bg-transparent p-1 text-gray-100';

function useWidth(ref, active = true) {
  const [width, setWidth] = useState(600);
  useEffect(() => {
    if (!active || !ref.current) return undefined;
    const observer = new ResizeObserver(entries => setWidth(Math.max(240, entries[0].contentRect.width)));
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [ref, active]);
  return width;
}

function SignalPlot({ title, unit, signals, time, boundaries, currentTime, onSeek, threshold, peaks, central }) {
  const ref = useRef(null);
  const width = useWidth(ref);
  const height = title === 'Pelvis height' ? 240 : 185;
  const left = 64, right = 15, top = 15, bottom = 39;
  const start = time[0], end = time.at(-1);
  const values = signals.flatMap(item => item.values).filter(Number.isFinite);
  const rawMin = values.reduce((a,b) => Math.min(a,b), threshold ?? Infinity);
  const rawMax = values.reduce((a,b) => Math.max(a,b), threshold ?? -Infinity);
  const padding = Math.max((rawMax - rawMin) * .12, .001);
  const min = rawMin - padding, max = rawMax + padding;
  const x = t => left + (t - start) / (end - start) * (width - left - right);
  const y = v => height - bottom - (v - min) / (max - min) * (height - top - bottom);
  const path = values => values.map((v, i) => `${i ? 'L' : 'M'}${x(time[i])},${y(v)}`).join(' ');
  const ticks = width < 450 ? 3 : 6;
  const clipId = `sts-clip-${title.replace(/\W/g, '')}`;
  return <div ref={ref} className="my-4 min-w-0">
    <h3 className="font-medium">{title}</h3>
    <div className="mb-2 text-xs text-gray-300">{unit}</div>
    {signals.length > 1 && <div className="mb-2 flex flex-wrap gap-4 text-xs">{signals.map(item => <span key={item.name}><span style={{ color: item.color }}>━━</span> {item.name}</span>)}</div>}
    <svg viewBox={`0 0 ${width} ${height}`} className="block w-full" role="img" aria-label={`${title} over time. Click to seek video.`} onClick={e => {
      const rect = e.currentTarget.getBoundingClientRect();
      const t = start + ((e.clientX - rect.left) * width / rect.width - left) / (width - left - right) * (end - start);
      onSeek(Math.max(start, Math.min(end, t)));
    }}>
      <defs><clipPath id={clipId}><rect x={left} y={top} width={width-left-right} height={height-top-bottom} /></clipPath></defs>
      {[0, 1, 2, 3].map(i => { const v = min + (max-min)*i/3; return <g key={i}><line x1={left} x2={width-right} y1={y(v)} y2={y(v)} stroke="#52525b" strokeWidth=".5" /><text x={left-8} y={y(v)+4} textAnchor="end" fill="#d4d4d8" fontSize="11">{v.toFixed(2)}</text></g>; })}
      {Array.from({ length: ticks }, (_, i) => start+(end-start)*i/(ticks-1)).map(t => <text key={t} x={x(t)} y={height-20} textAnchor="middle" fill="#d4d4d8" fontSize="11">{t.toFixed(2)}</text>)}
      <text x={width-right} y={height-2} textAnchor="end" fill="#d4d4d8" fontSize="12">Time (s)</text>
      <g clipPath={`url(#${clipId})`}>
        <rect x={x(boundaries.preparation_start)} y={top} width={Math.max(0,x(boundaries.rise_end)-x(boundaries.preparation_start))} height={height-top-bottom} fill={BLUE} opacity=".07" />
        {central && <rect x={x(central.start)} y={top} width={Math.max(0,x(central.end)-x(central.start))} height={height-top-bottom} fill={BLUE} opacity=".17" />}
        {threshold != null && <line x1={left} x2={width-right} y1={y(threshold)} y2={y(threshold)} stroke="#e4e4e7" strokeDasharray="6 4" />}
        {signals.map(item => <path key={item.name} d={path(item.values)} fill="none" stroke={item.color} strokeWidth="2" />)}
        {EVENTS.map(([key, label, color]) => <line key={key} x1={x(boundaries[key])} x2={x(boundaries[key])} y1={top} y2={height-bottom} stroke={color} strokeDasharray="4 4"><title>{`${label}: ${boundaries[key].toFixed(3)} s`}</title></line>)}
        {peaks?.time.map((t, i) => <circle key={i} cx={x(t)} cy={y(peaks.data[i])} r="4" fill={ORANGE} />)}
        {currentTime >= start && currentTime <= end && <line x1={x(currentTime)} x2={x(currentTime)} y1={top} y2={height-bottom} stroke="#f4f4f5" strokeWidth="1.5" />}
      </g>
    </svg>
  </div>;
}

export default function SitToStandGraphs({ selectedTaskIndex, tasks, setTasks, videoRef }) {
  const task = tasks?.[selectedTaskIndex];
  const data = task?.data;
  const sts = data?.sit_to_stand;
  const cache = data?.sit_to_stand_analysis_cache;
  const [draft, setDraft] = useState(sts?.boundaries || {});
  const [currentTime, setCurrentTime] = useState(0);
  const [showPreparation, setShowPreparation] = useState(true);
  const [showVelocity, setShowVelocity] = useState(false);
  const [showCentral, setShowCentral] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState(true);
  const timeline = useRef(null);
  const dragKey = useRef(null);
  const width = useWidth(timeline, Boolean(cache) && expanded);
  useEffect(() => { setDraft(sts?.boundaries || {}); setError(''); }, [sts, task?.id]);
  useEffect(() => {
    const video = videoRef?.current;
    if (!video) return undefined;
    const update = () => setCurrentTime(video.currentTime);
    update();
    video.addEventListener('timeupdate', update);
    video.addEventListener('seeked', update);
    return () => { video.removeEventListener('timeupdate', update); video.removeEventListener('seeked', update); };
  }, [videoRef, task?.id]);
  if (!sts || !cache) return <p className="p-4">Run sit-to-stand analysis to view the rise and review its boundaries.</p>;
  const signals = sts.signals;
  const time = signals.time;
  const start = time[0], end = time.at(-1), fps = cache.fps;
  const valid = EVENTS.every(([key]) => Number.isFinite(draft[key]) && draft[key] >= start && draft[key] <= end)
    && draft.preparation_start <= draft.rise_start && draft.rise_start < draft.rise_end;
  const seek = t => { if (videoRef?.current && Number.isFinite(t)) videoRef.current.currentTime = t; };
  const change = (key, value) => { setDraft(previous => ({ ...previous, [key]: value })); seek(value); };
  const apply = async restore => {
    setBusy(true); setError('');
    const taskId = task.id;
    try {
      const form = new FormData();
      form.append('json_data', JSON.stringify({ task_data: data, boundaries: draft, restore_automatic: restore }));
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'}/update_sit_to_stand/`, { method: 'POST', body: form });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Could not update the boundaries.');
      setTasks(previous => previous.map(item => item.id === taskId ? { ...item, data: result } : item));
    } catch (reason) { setError(reason.message); }
    finally { setBusy(false); }
  };
  const left = 16, right = 16;
  const tx = t => left+(t-start)/(end-start)*(width-left-right);
  const timelineTime = e => {
    const rect = e.currentTarget.getBoundingClientRect();
    const t = start+((e.clientX-rect.left)*width/rect.width-left)/(width-left-right)*(end-start);
    return Math.max(start, Math.min(end, start+Math.round((t-start)*fps)/fps));
  };
  const plot = (title, unit, series, extra = {}) => <SignalPlot title={title} unit={unit} signals={series} time={time} boundaries={sts.boundaries} currentTime={currentTime} onSeek={seek} central={showCentral ? sts.central_ascent : null} {...extra} />;
  return <div className="mx-4 text-gray-100">
    <div className="mb-4 rounded-lg border border-zinc-500 bg-zinc-700">
      <button type="button" className="w-full p-3 text-left" onClick={() => setExpanded(!expanded)} aria-expanded={expanded}>{expanded ? '▾' : '▸'} Analysis window</button>
      {expanded && <div className="border-t border-zinc-500 p-3">
        <div className="text-xs text-gray-300">Drag a marker or edit its time; the video follows. Apply to recalculate from saved landmarks.</div>
        <div ref={timeline}>
          <svg className="mt-2 block w-full touch-none" viewBox={`0 0 ${width} 64`} role="img" aria-label="Editable preparation and rise boundaries" onPointerMove={e => { if (dragKey.current) change(dragKey.current, timelineTime(e)); }} onPointerUp={e => { if (!dragKey.current) seek(timelineTime(e)); dragKey.current = null; }} onPointerCancel={() => { dragKey.current = null; }}>
            <rect x={left} y="18" width={width-left-right} height="20" fill="#52525b" rx="3" />
            <rect x={tx(draft.preparation_start ?? start)} y="18" width={Math.max(0,tx(draft.rise_end ?? end)-tx(draft.preparation_start ?? start))} height="20" fill={BLUE} opacity=".3" />
            {EVENTS.map(([key,label,color]) => Number.isFinite(draft[key]) && <g key={key} onPointerDown={e => { if (busy) return; e.stopPropagation(); dragKey.current = key; e.currentTarget.setPointerCapture(e.pointerId); seek(draft[key]); }} style={{ cursor: 'ew-resize' }}><line x1={tx(draft[key])} x2={tx(draft[key])} y1="8" y2="48" stroke={color} strokeWidth="3" /><rect x={tx(draft[key])-9} y="6" width="18" height="44" fill="transparent" /><title>{label}</title></g>)}
            <text x={left} y="61" fill="#d4d4d8" fontSize="11">{start.toFixed(2)} s</text><text x={width-right} y="61" textAnchor="end" fill="#d4d4d8" fontSize="11">{end.toFixed(2)} s</text>
          </svg>
        </div>
        <div className="mt-2 flex flex-wrap gap-3">{EVENTS.map(([key,label,color]) => <label key={key} className="flex flex-wrap items-center gap-2 text-sm"><span style={{ color }}>┆</span>{label}<input aria-label={label} className={inputClass} type="number" min={start} max={end} step={1/fps} value={Number.isFinite(draft[key]) ? Number(draft[key].toFixed(4)) : ''} onChange={e => change(key,e.target.value === '' ? NaN : Number(e.target.value))} disabled={busy} /></label>)}</div>
        <div className="mt-3 flex flex-wrap gap-3"><button type="button" disabled={busy || !valid} className="rounded bg-[#1976d2] px-3 py-1 disabled:opacity-50" onClick={() => apply(false)}>{busy ? 'Recalculating…' : 'Apply boundaries'}</button><button type="button" className="rounded border border-zinc-400 px-3 py-1 disabled:opacity-50" disabled={busy} onClick={() => apply(true)}>Restore automatic</button></div>
        {!valid && <p role="alert" className="mt-2 text-sm text-orange-300">Choose preparation onset ≤ upward-ascent onset &lt; pelvic movement end, within the recording.</p>}
        {error && <p role="alert" className="mt-2 text-sm text-red-300">{error}</p>}
      </div>}
    </div>
    <div className="flex flex-wrap gap-4 text-sm"><label><input type="checkbox" checked={showPreparation} onChange={e => setShowPreparation(e.target.checked)} /> Preparation signals</label><label><input type="checkbox" checked={showVelocity} onChange={e => setShowVelocity(e.target.checked)} /> Velocity &amp; peaks</label><label><input type="checkbox" checked={showCentral} onChange={e => setShowCentral(e.target.checked)} /> 10–90% interval</label></div>
    <div className="mt-3 flex flex-wrap gap-3 text-xs">{EVENTS.map(([key,label,color]) => <span key={key}><span style={{ color }}>┆</span> {label}: {sts.boundaries[key].toFixed(3)} s</span>)}</div>
    {plot('Pelvis height','Relative to ankle midpoint · Body-size reference units',[{ name:'Pelvis height',values:signals.pelvis_height,color:BLUE }])}
    {showPreparation && plot('Preparation signals','Departure ÷ detection threshold · Threshold = 1',[{ name:'Pelvis departure',values:signals.pelvis_evidence,color:BLUE },{ name:'Shoulder movement relative to pelvis',values:signals.shoulder_evidence,color:ORANGE }],{ threshold:1 })}
    {showVelocity && plot('Pelvis vertical velocity','Image-vertical velocity (pixels/s) · Peaks counted from absolute speed',[{ name:'Vertical velocity',values:signals.pelvis_velocity,color:BLUE }],{ peaks:sts.speed_peaks })}
    <p className="text-xs text-gray-300">{sts.reviewed ? 'Reviewed boundaries applied.' : 'Automatic boundaries; review in the video.'} Motion feature window: {sts.feature_window.start.toFixed(3)}–{sts.feature_window.end.toFixed(3)} s ({sts.feature_window.source === 'automatic_5_95' ? 'automatic 5–95% rise' : 'reviewed rise interval'}). Central ascent time remains the automatic 10–90% measurement.</p>
    <p className="mt-2 text-xs text-gray-300">Pelvic movement end does not confirm full upright posture. Arm geometry does not establish hand support. Metric height scaling is not applied.</p>
    {sts.quality.warnings.map((warning,i) => <p key={i} className="mt-2 text-sm text-orange-300">{warning}</p>)}
  </div>;
}
