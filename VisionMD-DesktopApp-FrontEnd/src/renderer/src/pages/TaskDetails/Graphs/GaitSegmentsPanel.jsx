import { useEffect, useMemo, useState } from 'react';
import VideoSegmentsTimeline from './VideoSegmentsTimeline';
import AnalysisWindowPanel from './AnalysisWindowPanel';

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const numberValue = value => value === '' ? NaN : Number(value);
const inputClass = 'ml-1 w-24 rounded border border-zinc-500 bg-transparent p-1';

export default function GaitSegmentsPanel({ selectedTaskIndex, tasks, setTasks, videoRef }) {
  const task = tasks?.[selectedTaskIndex];
  const data = task?.data ?? {};
  const cache = data.gait_analysis_cache;
  const metadata = data.turning_metadata;
  const fps = Number(cache?.fps || 0);
  const cacheStart = Number(cache?.start_time ?? task?.start ?? 0);
  const count = cache?.poses3d?.length || 0;
  const cacheEnd = count > 1 && fps > 0 ? cacheStart + (count - 1) / fps : Number(task?.end ?? cacheStart);
  const detectedTurns = useMemo(() => {
    const list = metadata?.turns ?? (metadata?.is_turning ? [metadata] : []);
    return list.map(item => ({ start: Number(item.start_time_seconds), end: Number(item.end_time_seconds) }));
  }, [metadata]);
  const [turns, setTurns] = useState(detectedTurns);
  const [walking, setWalking] = useState(data.walking_range || { start: cacheStart, end: cacheEnd });
  const [expanded, setExpanded] = useState(true);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { setTurns(detectedTurns); }, [detectedTurns]);
  useEffect(() => { setWalking(data.walking_range || { start: cacheStart, end: cacheEnd }); }, [data.walking_range, cacheStart, cacheEnd]);
  const regions = useMemo(() => {
    const result = [];
    if (!Number.isFinite(walking.start) || !Number.isFinite(walking.end) || walking.end <= walking.start) return result;
    let start = walking.start;
    const walkingRegion = (a,b,index,last) => {
      if (b > a) result.push({ id: `walking-${index}`, start: a, end: b, drag: false,
        resize: index === 0 || last, resizeStart: index === 0, resizeEnd: last,
        color: index % 2 ? 'rgba(34,197,94,0.28)' : 'rgba(37,99,235,0.30)' });
    };
    turns.forEach((turn,index) => {
      if (!Number.isFinite(turn.start) || !Number.isFinite(turn.end)) return;
      const a = clamp(turn.start,walking.start,walking.end), b = clamp(turn.end,a,walking.end);
      walkingRegion(start,a,index,false);
      if (b > a) result.push({ id: `turn-${index}`, start: a, end: b, drag: true, resize: true, color: 'rgba(239,68,68,0.42)' });
      start = b;
    });
    walkingRegion(start,walking.end,turns.length,true);
    return result;
  }, [turns, walking]);
  const updateRegion = region => {
    const gap = fps > 0 ? 1/fps : .001;
    if (region.id.startsWith('turn-')) {
      const index = Number(region.id.slice(5));
      const minimum = turns[index-1] ? turns[index-1].end+gap : walking.start;
      const maximum = turns[index+1] ? turns[index+1].start-gap : walking.end;
      const start = clamp(Number(region.start.toFixed(3)),minimum,maximum-gap);
      const end = clamp(Number(region.end.toFixed(3)),start+gap,maximum);
      setTurns(previous => previous.map((item,i) => i === index ? { start,end } : item));
    } else {
      setWalking({ start: region.id === 'walking-0' ? clamp(Number(region.start.toFixed(3)),cacheStart,(turns[0]?.start ?? walking.end)-gap) : walking.start,
        end: region.id === `walking-${turns.length}` ? clamp(Number(region.end.toFixed(3)),(turns.at(-1)?.end ?? walking.start)+gap,cacheEnd) : walking.end });
    }
  };

  const invalid = !Number.isFinite(walking.start) || !Number.isFinite(walking.end)
    || walking.start < cacheStart || walking.end > cacheEnd || walking.end <= walking.start
    || turns.some((turn, i) => !Number.isFinite(turn.start) || !Number.isFinite(turn.end)
      || turn.start < walking.start || turn.end > walking.end || turn.end <= turn.start
      || (i > 0 && turn.start <= turns[i - 1].end));
  const apply = async (redetect = false) => {
    setApplying(true); setError('');
    try {
      const form = new FormData();
      form.append('json_data', JSON.stringify({ task_data: data, walking_range: walking,
        redetect_turns: redetect,
        turning_segments: turns.map(turn => ({ start_time_seconds: turn.start, end_time_seconds: turn.end })) }));
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'}/update_gait_segments/`, { method: 'POST', body: form });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || `Server returned ${response.status}`);
      setTasks(previous => previous.map((item, i) => i === selectedTaskIndex ? { ...item, data: result } : item));
    } catch (reason) { setError(reason.message || 'Could not update gait segments.'); }
    finally { setApplying(false); }
  };
  const addTurn = () => {
    const gaps = [];
    let start = walking.start;
    turns.forEach(turn => { gaps.push({ start, end: turn.start }); start = turn.end; });
    gaps.push({ start, end: walking.end });
    const gap = gaps.sort((a, b) => (b.end - b.start) - (a.end - a.start))[0];
    if (!gap || gap.end - gap.start < 0.2) return;
    const middle = (gap.start + gap.end) / 2;
    const half = Math.min(0.5, (gap.end - gap.start) / 4);
    setTurns([...turns, { start: middle - half, end: middle + half }].sort((a, b) => a.start - b.start));
  };
  const input = (label, value, min, max, onChange) => <label className="flex shrink-0 items-center whitespace-nowrap">{label}<input aria-label={label} className={inputClass} type="number" step="0.001" min={min} max={max} value={Number.isFinite(value) ? value : ''} onChange={e => onChange(numberValue(e.target.value))} /></label>;
  return <AnalysisWindowPanel title="Walking & turning segments" expanded={expanded} onToggle={() => setExpanded(!expanded)} description={`Cached gait range: ${cacheStart.toFixed(3)}–${cacheEnd.toFixed(3)} s. Drag colored edges to adjust times; click to seek.`}>
      <VideoSegmentsTimeline videoRef={videoRef} start={cacheStart} end={cacheEnd} regions={regions} onRegionUpdated={updateRegion} disabled={applying} label="Walking and turning intervals" />
      <div className="mt-2 text-xs">Blue/green: walking intervals · Red: {metadata?.transition_guard_seconds > 0 ? 'saved padded turn intervals — redetect to update' : 'estimated turns (no added time margin)'}</div>
      <div className="mt-3 flex items-center gap-3 overflow-x-auto">
        {input('Walking start', walking.start, cacheStart, turns[0]?.start ?? walking.end, value => setWalking({ ...walking, start: value }))}
        {input('Walking end', walking.end, turns.at(-1)?.end ?? walking.start, cacheEnd, value => setWalking({ ...walking, end: value }))}
      </div>
      {turns.map((turn, index) => <div key={index} className="mt-3 flex items-center gap-3 overflow-x-auto">
        {input(`Turn ${index + 1} start`, turn.start, turns[index - 1]?.end ?? walking.start, turn.end, value => setTurns(turns.map((item, i) => i === index ? { ...item, start: value } : item)))}
        {input(`Turn ${index + 1} end`, turn.end, turn.start, turns[index + 1]?.start ?? walking.end, value => setTurns(turns.map((item, i) => i === index ? { ...item, end: value } : item)))}
        <button type="button" className="shrink-0 rounded border border-red-400 px-2 py-1" onClick={() => setTurns(turns.filter((_, i) => i !== index))}>Remove turn {index + 1}</button>
      </div>)}
      {!turns.length && <div className="mt-2 text-sm">No turns selected.</div>}
      <div className="mt-3 flex flex-wrap gap-3">
        <button type="button" className="rounded border px-2 py-1" onClick={addTurn} disabled={!cache || applying || invalid}>Add turn</button>
        <button type="button" className="rounded border px-2 py-1" onClick={() => apply(true)} disabled={!cache || applying || !Number.isFinite(walking.start) || !Number.isFinite(walking.end)}>Redetect turns from cached poses</button>
        <button type="button" className="rounded bg-[#1976d2] px-3 py-1 disabled:opacity-50" onClick={() => apply()} disabled={!cache || applying || invalid}>{applying ? 'Recalculating…' : 'Apply from cached gait landmarks'}</button>
      </div>
      {metadata?.transition_guard_seconds > 0 && <div className="mt-2 text-sm">These saved results used padded turn boundaries. Redetect turns to update them.</div>}
      {invalid && <div role="alert" className="mt-2 text-sm text-red-400">Choose ordered, non-overlapping turns inside the walking range.</div>}
      {!cache && <div className="mt-2 text-sm">This older result has no cached poses. Run gait analysis to edit intervals.</div>}
      {error && <div role="alert" className="mt-2 text-sm text-red-400">{error}</div>}
  </AnalysisWindowPanel>;
}
