import { useEffect, useMemo, useState } from 'react';
import GaitGraphs from './GaitGraphs';
import AnalysisWindowPanel from './AnalysisWindowPanel';
import VideoSegmentsTimeline from './VideoSegmentsTimeline';
import { reviewedBoundary } from './sitToStandBoundaries';

const EVENTS = [
  ['preparation_start', 'Preparation onset', '#c084fc'],
  ['rise_start', 'Upward-ascent onset', '#fb923c'],
  ['rise_end', 'Pelvic movement end', '#4ade80'],
];
const BLUE = '#60a5fa';
const ORANGE = '#fb923c';
const inputClass = 'ml-1 w-24 rounded border border-zinc-500 bg-transparent p-1';

export default function SitToStandGraphs({ selectedTaskIndex, tasks, setTasks, videoRef }) {
  const task = tasks?.[selectedTaskIndex];
  const data = task?.data;
  const sts = data?.sit_to_stand;
  const cache = data?.sit_to_stand_analysis_cache;
  const [draft, setDraft] = useState(sts?.boundaries || {});
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
  const plotGroups = [
    {key:'pelvis_height',title:'Pelvis height',unit:'Relative to ankle midpoint · Body-size reference units',axisLabel:'Pelvis height (relative)',time,series:[{name:'Pelvis height',values:signals.pelvis_height,color:BLUE}]},
    {key:'preparation',title:'Preparation signals',unit:'Departure ÷ detection threshold · Threshold = 1',axisLabel:'Departure / threshold',time,series:[{name:'Pelvis departure',values:signals.pelvis_evidence,color:BLUE},{name:'Shoulder movement relative to pelvis',values:signals.shoulder_evidence,color:ORANGE}],threshold:1},
    {key:'velocity',title:'Pelvis vertical velocity',unit:'Image-vertical velocity (pixels/s) · Peaks counted from absolute speed',axisLabel:'Velocity (pixels/s)',time,series:[{name:'Vertical velocity',values:signals.pelvis_velocity,color:BLUE}],peaks:sts.speed_peaks},
  ];
  return <div className="text-gray-100">
    <AnalysisWindowPanel title="Preparation & rise segments" expanded={expanded} onToggle={() => setExpanded(!expanded)} description={`Cached sit-to-stand range: ${start.toFixed(3)}–${end.toFixed(3)} s. Drag markers to adjust times; click to seek.`}>
        <VideoSegmentsTimeline videoRef={videoRef} start={start} end={end} regions={regions} onRegionUpdated={updateRegion} disabled={busy} label="Editable preparation and rise boundaries" />
        <div className="mt-2 text-xs">Purple: preparation onset · Orange: upward-ascent onset · Green: pelvic movement end</div>
        <div className="mt-3 flex flex-wrap items-center gap-3">{EVENTS.map(([key,label]) => <label key={key} className="flex shrink-0 items-center whitespace-nowrap">{label}<input aria-label={label} className={inputClass} type="number" min={start} max={end} step={1/fps} value={Number.isFinite(draft[key]) ? Number(draft[key].toFixed(4)) : ''} onChange={e => change(key,e.target.value === '' ? NaN : Number(e.target.value))} disabled={busy} /></label>)}</div>
        <div className="mt-3 flex flex-wrap gap-3"><button type="button" disabled={busy || !valid} className="rounded bg-[#1976d2] px-3 py-1 disabled:opacity-50" onClick={() => apply(false)}>{busy ? 'Recalculating…' : 'Apply from cached sit-to-stand landmarks'}</button><button type="button" className="rounded border border-zinc-400 px-3 py-1 disabled:opacity-50" disabled={busy} onClick={() => apply(true)}>Restore automatic</button></div>
        {!valid && <p role="alert" className="mt-2 text-sm text-orange-300">Choose preparation onset ≤ upward-ascent onset &lt; pelvic movement end, within the recording.</p>}
        {error && <p role="alert" className="mt-2 text-sm text-red-300">{error}</p>}
    </AnalysisWindowPanel>
    <GaitGraphs selectedTaskIndex={selectedTaskIndex} tasks={tasks} videoRef={videoRef} plotGroups={plotGroups} initialSignal="pelvis_height" signalLabel="Sit-to-stand signal" markers={markers} bands={bands}
      controls={<label><input type="checkbox" checked={showCentral} onChange={e => setShowCentral(e.target.checked)} /> 10–90% interval</label>}
      eventLegend={EVENTS.map(([key,label,color]) => <span key={key}><span style={{color}}>┆</span> {label}: {sts.boundaries[key].toFixed(3)} s</span>)} />
    <div className="mx-4 mt-4">
    <p className="text-xs text-gray-300">{sts.reviewed ? 'Reviewed boundaries applied.' : 'Automatic boundaries; review in the video.'} Motion feature window: {sts.feature_window.start.toFixed(3)}–{sts.feature_window.end.toFixed(3)} s ({sts.feature_window.source === 'automatic_5_95' ? 'automatic 5–95% rise' : 'reviewed rise interval'}). Central ascent time remains the automatic 10–90% measurement.</p>
    <p className="mt-2 text-xs text-gray-300">Pelvic movement end does not confirm full upright posture. Arm geometry does not establish hand support. Metric height scaling is not applied.</p>
    {sts.quality.warnings.map((warning,i) => <p key={i} className="mt-2 text-sm text-orange-300">{warning}</p>)}
    </div>
  </div>;
}
