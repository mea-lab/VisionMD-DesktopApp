import { useEffect, useMemo, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';
import RegionsPlugin from 'wavesurfer.js/plugins/regions';
import HoverPlugin from 'wavesurfer.js/plugins/hover';

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
  const waveformRef = useRef(null);
  const waveRef = useRef(null);
  const regionsRef = useRef(null);
  const syncing = useRef(false);
  const current = useRef({ turns, walking });
  current.current = { turns, walking };
  useEffect(() => { setTurns(detectedTurns); }, [detectedTurns]);
  useEffect(() => { setWalking(data.walking_range || { start: cacheStart, end: cacheEnd }); }, [data.walking_range, cacheStart, cacheEnd]);

  const renderRegions = () => {
    const regions = regionsRef.current;
    if (!regions) return;
    syncing.current = true;
    regions.clearRegions();
    const { turns: intervals, walking: range } = current.current;
    if (!Number.isFinite(range.start) || !Number.isFinite(range.end) || range.end <= range.start) {
      syncing.current = false;
      return;
    }
    let start = range.start;
    const walkingRegion = (a, b, index, last) => {
      if (b <= a) return;
      regions.addRegion({ id: `walking-${index}`, start: a, end: b, drag: false,
        resize: index === 0 || last, resizeStart: index === 0, resizeEnd: last,
        color: index % 2 ? 'rgba(34,197,94,0.28)' : 'rgba(37,99,235,0.30)' });
    };
    intervals.forEach((turn, index) => {
      if (!Number.isFinite(turn.start) || !Number.isFinite(turn.end)) return;
      const a = clamp(turn.start, range.start, range.end);
      const b = clamp(turn.end, a, range.end);
      walkingRegion(start, a, index, false);
      if (b > a) regions.addRegion({ id: `turn-${index}`, start: a, end: b,
        drag: true, resize: true, color: 'rgba(239,68,68,0.42)' });
      start = b;
    });
    walkingRegion(start, range.end, intervals.length, true);
    syncing.current = false;
  };

  useEffect(() => {
    if (!expanded || !videoRef.current || !waveformRef.current || cacheEnd <= cacheStart) return;
    const video = videoRef.current;
    const preview = new Audio(video.currentSrc || video.src);
    const wave = WaveSurfer.create({ container: waveformRef.current, media: preview,
      height: 82, waveColor: '#6b7280', progressColor: '#374151', cursorColor: '#111827',
      cursorWidth: 3, barWidth: 2, barRadius: 2, normalize: true });
    const regions = wave.registerPlugin(RegionsPlugin.create());
    wave.registerPlugin(HoverPlugin.create({ lineColor: '#111827', lineWidth: 1,
      labelBackground: '#18181b', labelColor: '#f3f4f6', labelSize: '12px',
      formatTimeCallback: seconds => `${seconds.toFixed(3)} s` }));
    waveRef.current = wave;
    regionsRef.current = regions;
    wave.on('ready', () => { wave.zoom(Math.max(1, 720 / (video.duration || cacheEnd))); renderRegions(); });
    regions.on('region-updated', region => {
      if (syncing.current) return;
      const { turns: intervals, walking: range } = current.current;
      const gap = fps > 0 ? 1 / fps : 0.001;
      if (region.id.startsWith('turn-')) {
        const index = Number(region.id.slice(5));
        const minimum = intervals[index - 1]?.end + gap || range.start;
        const maximum = intervals[index + 1]?.start - gap || range.end;
        const start = clamp(Number(region.start.toFixed(3)), minimum, maximum - gap);
        const end = clamp(Number(region.end.toFixed(3)), start + gap, maximum);
        setTurns(previous => previous.map((item, i) => i === index ? { start, end } : item));
      } else {
        const first = region.id === 'walking-0';
        const last = region.id === `walking-${intervals.length}`;
        setWalking({ start: first ? clamp(Number(region.start.toFixed(3)), cacheStart, (intervals[0]?.start ?? range.end) - gap) : range.start,
          end: last ? clamp(Number(region.end.toFixed(3)), (intervals.at(-1)?.end ?? range.start) + gap, cacheEnd) : range.end });
      }
    });
    wave.on('interaction', time => { video.currentTime = time; });
    const sync = () => { if (Number.isFinite(video.currentTime)) wave.setTime(video.currentTime); };
    video.addEventListener('timeupdate', sync);
    video.addEventListener('seeked', sync);
    return () => {
      video.removeEventListener('timeupdate', sync);
      video.removeEventListener('seeked', sync);
      wave.destroy(); preview.pause(); preview.removeAttribute('src'); preview.load();
      waveRef.current = null; regionsRef.current = null;
    };
  }, [expanded, videoRef, cacheStart, cacheEnd]);
  useEffect(() => { renderRegions(); }, [turns, walking]);

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
  return <div className="mb-6 rounded-lg border border-zinc-600 bg-zinc-700">
    <button type="button" className="w-full px-4 py-2 text-left font-semibold" onClick={() => setExpanded(!expanded)}>{expanded ? '▾' : '▸'} Walking &amp; turning segments</button>
    {expanded && <div className="border-t border-zinc-600 p-3">
      <div className="mb-2 text-xs">Cached gait range: {cacheStart.toFixed(3)}–{cacheEnd.toFixed(3)} s. Drag colored edges to adjust times; click to seek.</div>
      <div ref={waveformRef} className="overflow-x-auto rounded bg-zinc-800" />
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
    </div>}
  </div>;
}
