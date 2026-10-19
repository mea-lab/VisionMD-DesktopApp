import { useEffect, useMemo, useState } from 'react';
import VideoSignalPlot from './VideoSignalPlot';
import VideoSegmentsTimeline from './VideoSegmentsTimeline';
import { reviewedBoundary } from './sitToStandBoundaries';

const EVENTS = [
  ['preparation_start', 'Preparation onset', '#c084fc'],
  ['rise_start', 'Upward-ascent onset', '#fb923c'],
  ['rise_end', 'Pelvic movement end', '#4ade80'],
];
const BLUE = '#60a5fa';
const ORANGE = '#fb923c';
const inputClass = 'w-24 rounded border border-zinc-500 bg-transparent p-1 text-gray-100';

export default function SitToStandGraphs({ selectedTaskIndex, tasks, setTasks, videoRef }) {
  const task = tasks?.[selectedTaskIndex];
  const data = task?.data;
  const sts = data?.sit_to_stand;
  const cache = data?.sit_to_stand_analysis_cache;
  const [draft, setDraft] = useState(sts?.boundaries || {});
  const [showPreparation, setShowPreparation] = useState(true);
  const [showVelocity, setShowVelocity] = useState(false);
  const [showCentral, setShowCentral] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState(true);
  useEffect(() => { setDraft(sts?.boundaries || {}); setError(''); }, [sts, task?.id]);
  const regions = useMemo(() => {
    const result = [];
    if (Number.isFinite(draft.preparation_start) && Number.isFinite(draft.rise_end) && draft.rise_end > draft.preparation_start) {
      result.push({ id:'analysis', start:draft.preparation_start, end:draft.rise_end, drag:false, resize:false, color:'rgba(96,165,250,.15)' });
    }
    EVENTS.forEach(([key,,color]) => {
      if (Number.isFinite(draft[key])) result.push({ id:key,start:draft[key],drag:true,resize:false,color });
    });
    return result;
  }, [draft]);
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
  const updateRegion = region => {
    if (!EVENTS.some(([key]) => key === region.id)) return;
    change(region.id,reviewedBoundary(region.id,region.start,draft,start,end,fps));
  };
  const markers = EVENTS.map(([key,label,color]) => ({time:sts.boundaries[key],label,color}));
  const bands = [{start:sts.boundaries.preparation_start,end:sts.boundaries.rise_end,color:'rgba(96,165,250,.07)'},
    ...(showCentral ? [{...sts.central_ascent,color:'rgba(96,165,250,.17)'}] : [])];
  const plot = (title, unit, series, extra = {}) => <VideoSignalPlot title={title} unit={unit} axisLabel={title === 'Pelvis height' ? 'Pelvis height (relative)' : title === 'Preparation signals' ? 'Departure / threshold' : 'Velocity (pixels/s)'} series={series} time={time} videoRef={videoRef} markers={markers} bands={bands} height={title === 'Pelvis height' ? 280 : 230} {...extra} />;
  return <div className="mx-4 text-gray-100">
    <div className="mb-4 rounded-lg border border-zinc-500 bg-zinc-700">
      <button type="button" className="w-full p-3 text-left" onClick={() => setExpanded(!expanded)} aria-expanded={expanded}>{expanded ? '▾' : '▸'} Analysis window</button>
      {expanded && <div className="border-t border-zinc-500 p-3">
        <div className="text-xs text-gray-300">Drag a marker or edit its time; the video follows. Apply to recalculate from saved landmarks.</div>
        <VideoSegmentsTimeline videoRef={videoRef} start={start} end={end} regions={regions} onRegionUpdated={updateRegion} previewSignal={signals.pelvis_height} previewStart={start} fps={fps} disabled={busy} label="Editable preparation and rise boundaries" />
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
