import { useEffect, useMemo, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';
import RegionsPlugin from 'wavesurfer.js/plugins/regions';
import HoverPlugin from 'wavesurfer.js/plugins/hover';

const clamp = (value, minimum, maximum) =>
  Math.min(maximum, Math.max(minimum, value));

const GaitSegmentsPanel = ({
  selectedTaskIndex,
  tasks,
  setTasks,
  videoRef,
}) => {
  const task = tasks?.[selectedTaskIndex];
  const data = task?.data ?? {};
  const cache = data.gait_analysis_cache;
  const metadata = data.turning_metadata ?? {};
  const waveformRef = useRef(null);
  const waveRef = useRef(null);
  const regionsRef = useRef(null);
  const previewMediaRef = useRef(null);
  const syncingRef = useRef(false);

  const fps = Number(cache?.fps || 0);
  const cacheStart = Number(cache?.start_time ?? task?.start ?? 0);
  const cachedFrames = cache?.poses3d?.length ?? 0;
  const cacheEnd = Number(
    cachedFrames > 1 && fps > 0
      ? cacheStart + (cachedFrames - 1) / fps
      : task?.end ?? cacheStart
  );
  const detectedRange = useMemo(() => {
    if (metadata.is_turning) {
      return {
        start: Number(metadata.start_time_seconds),
        end: Number(metadata.end_time_seconds),
      };
    }
    const middle = (cacheStart + cacheEnd) / 2;
    const halfWidth = Math.min(0.5, (cacheEnd - cacheStart) / 10);
    return { start: middle - halfWidth, end: middle + halfWidth };
  }, [metadata.is_turning, metadata.start_time_seconds, metadata.end_time_seconds, cacheStart, cacheEnd]);

  const [expanded, setExpanded] = useState(true);
  const [hasTurn, setHasTurn] = useState(Boolean(metadata.is_turning));
  const [turnRange, setTurnRange] = useState(detectedRange);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setHasTurn(Boolean(metadata.is_turning));
    setTurnRange(detectedRange);
  }, [metadata.is_turning, detectedRange]);

  const renderRegions = (turnEnabled, range) => {
    const regions = regionsRef.current;
    if (!regions) return;
    syncingRef.current = true;
    regions.clearRegions();
    if (!turnEnabled) {
      regions.addRegion({
        id: 'walking-all', start: cacheStart, end: cacheEnd,
        drag: false, resize: false, color: 'rgba(37, 99, 235, 0.30)',
      });
    } else {
      const start = clamp(range.start, cacheStart, cacheEnd);
      const end = clamp(range.end, start, cacheEnd);
      if (start > cacheStart) {
        regions.addRegion({
          id: 'walking-before', start: cacheStart, end: start,
          drag: false, resize: false, color: 'rgba(37, 99, 235, 0.30)',
        });
      }
      regions.addRegion({
        id: 'turn', start, end, drag: true, resize: true,
        color: 'rgba(239, 68, 68, 0.42)',
      });
      if (end < cacheEnd) {
        regions.addRegion({
          id: 'walking-after', start: end, end: cacheEnd,
          drag: false, resize: false, color: 'rgba(34, 197, 94, 0.28)',
        });
      }
    }
    syncingRef.current = false;
  };

  useEffect(() => {
    if (!expanded || !videoRef.current || !waveformRef.current || cacheEnd <= cacheStart) return;
    const previewMedia = new Audio(videoRef.current.currentSrc || videoRef.current.src);
    previewMediaRef.current = previewMedia;
    const wave = WaveSurfer.create({
      container: waveformRef.current,
      media: previewMedia,
      height: 82,
      waveColor: '#6b7280',
      progressColor: '#374151',
      cursorColor: '#f3f4f6',
      barWidth: 2,
      barRadius: 2,
      normalize: true,
    });
    const regions = wave.registerPlugin(RegionsPlugin.create());
    wave.registerPlugin(HoverPlugin.create({
      lineColor: '#f3f4f6', lineWidth: 1,
      labelBackground: '#18181b', labelColor: '#f3f4f6', labelSize: '12px',
      formatTimeCallback: seconds => `${seconds.toFixed(3)} s`,
    }));
    waveRef.current = wave;
    regionsRef.current = regions;

    wave.on('ready', () => {
      const duration = videoRef.current?.duration || cacheEnd;
      wave.zoom(Math.max(1, 720 / duration));
      renderRegions(Boolean(metadata.is_turning), detectedRange);
    });
    regions.on('region-updated', region => {
      if (syncingRef.current || region.id !== 'turn') return;
      const next = {
        start: Number(region.start.toFixed(3)),
        end: Number(region.end.toFixed(3)),
      };
      setTurnRange(next);
      // Walking regions are always the complement of the selected turn.
      renderRegions(true, next);
    });
    wave.on('interaction', time => {
      if (videoRef.current) videoRef.current.currentTime = time;
    });
    const syncToVideo = () => {
      if (Number.isFinite(videoRef.current?.currentTime)) {
        wave.setTime(videoRef.current.currentTime);
      }
    };
    videoRef.current.addEventListener('timeupdate', syncToVideo);
    videoRef.current.addEventListener('seeked', syncToVideo);

    return () => {
      videoRef.current?.removeEventListener('timeupdate', syncToVideo);
      videoRef.current?.removeEventListener('seeked', syncToVideo);
      wave.destroy();
      previewMedia.pause();
      previewMedia.removeAttribute('src');
      previewMedia.load();
      waveRef.current = null;
      regionsRef.current = null;
    };
  }, [expanded, videoRef, cacheStart, cacheEnd]);

  useEffect(() => {
    if (waveRef.current) renderRegions(hasTurn, turnRange);
  }, [hasTurn]);

  const updateBoundary = (field, rawValue) => {
    const value = Number(rawValue);
    const next = {
      ...turnRange,
      [field]: value,
    };
    setTurnRange(next);
    renderRegions(hasTurn, next);
  };

  const applySegments = async () => {
    setApplying(true);
    setError('');
    try {
      const form = new FormData();
      form.append('json_data', JSON.stringify({
        task_data: data,
        turning_segment: {
          is_turning: hasTurn,
          start_time_seconds: turnRange.start,
          end_time_seconds: turnRange.end,
        },
      }));
      const response = await fetch('http://localhost:8000/api/update_gait_segments/', {
        method: 'POST', body: form,
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || `Server returned ${response.status}`);
      setTasks(previous => previous.map((item, index) =>
        index === selectedTaskIndex ? { ...item, data: result } : item
      ));
    } catch (reason) {
      setError(reason.message || 'Could not update gait segments.');
    } finally {
      setApplying(false);
    }
  };

  const invalidRange = hasTurn && (
    turnRange.start < cacheStart || turnRange.end > cacheEnd ||
    turnRange.end <= turnRange.start
  );

  return (
    <div className="mb-6 rounded-lg border border-zinc-600 bg-zinc-700">
      <button
        type="button"
        className="w-full px-4 py-2 text-left font-semibold hover:bg-zinc-600"
        onClick={() => setExpanded(value => !value)}
      >
        {expanded ? '▾' : '▸'} Walking &amp; turning segments
      </button>
      {expanded && (
        <div className="border-t border-zinc-600 p-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs text-zinc-200">
            <span>Cached gait range: {cacheStart.toFixed(3)}–{cacheEnd.toFixed(3)} s</span>
            <span>Hover for exact time; click to seek the video</span>
          </div>
          <div ref={waveformRef} className="overflow-x-auto rounded bg-zinc-800" />
          <div className="mt-2 flex flex-wrap gap-4 text-xs">
            <span><i className="mr-1 inline-block h-3 w-3 bg-blue-600/70" />Walking segment 1</span>
            <span><i className="mr-1 inline-block h-3 w-3 bg-red-500/70" />Turn</span>
            <span><i className="mr-1 inline-block h-3 w-3 bg-green-500/70" />Walking segment 2</span>
          </div>
          <div className="mt-3 flex flex-wrap items-end gap-3 text-sm">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={hasTurn}
                onChange={event => {
                  const enabled = event.target.checked;
                  if (enabled && turnRange.end <= turnRange.start) {
                    const middle = (cacheStart + cacheEnd) / 2;
                    const halfWidth = Math.min(0.5, (cacheEnd - cacheStart) / 10);
                    setTurnRange({ start: middle - halfWidth, end: middle + halfWidth });
                  }
                  setHasTurn(enabled);
                }}
              />
              Turn present
            </label>
            {hasTurn && <>
              <label>Turn start <input className="ml-1 w-24 rounded border border-zinc-500 bg-zinc-800 p-1" type="number" step="0.001" min={cacheStart} max={turnRange.end} value={turnRange.start} onChange={event => updateBoundary('start', event.target.value)} /></label>
              <label>Turn end <input className="ml-1 w-24 rounded border border-zinc-500 bg-zinc-800 p-1" type="number" step="0.001" min={turnRange.start} max={cacheEnd} value={turnRange.end} onChange={event => updateBoundary('end', event.target.value)} /></label>
            </>}
            <button
              type="button"
              className="rounded bg-[#1976d2] px-3 py-1 hover:bg-[#1565c0] disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!cache || applying || invalidRange}
              onClick={applySegments}
            >
              {applying ? 'Recalculating…' : 'Apply from cached gait landmarks'}
            </button>
          </div>
          {!cache && <div className="mt-2 text-sm text-amber-300">This older JSON can display its detected segments, but it does not contain the cached gait data required to edit them.</div>}
          {error && <div className="mt-2 text-sm text-red-400">{error}</div>}
        </div>
      )}
    </div>
  );
};

export default GaitSegmentsPanel;
