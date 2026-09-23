import { useEffect, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';
import RegionsPlugin from 'wavesurfer.js/plugins/regions';
import HoverPlugin from 'wavesurfer.js/plugins/hover';

const AnalysisRangePanel = ({ videoRef, cacheStart, cacheEnd, start, end, normStrategy, onApply }) => {
  const waveformRef = useRef(null);
  const waveRef = useRef(null);
  const regionsRef = useRef(null);
  const previewMediaRef = useRef(null);
  const syncingRef = useRef(false);
  const [range, setRange] = useState({ start, end });
  const [strategy, setStrategy] = useState(normStrategy || 'INDEXSIZE');

  useEffect(() => setRange({ start, end }), [start, end]);
  useEffect(() => setStrategy(normStrategy || 'INDEXSIZE'), [normStrategy]);

  useEffect(() => {
    if (!videoRef.current || !waveformRef.current) return;
    // Do not pass the review screen's video element to WaveSurfer.  WaveSurfer
    // attaches its own media/event handlers; sharing that element made Plotly
    // clicks and video seeking unreliable.  A separate audio element provides
    // the waveform while leaving the review video fully under its own control.
    const previewMedia = new Audio(videoRef.current.currentSrc || videoRef.current.src);
    previewMediaRef.current = previewMedia;
    const wave = WaveSurfer.create({
      container: waveformRef.current, media: previewMedia, height: 76,
      waveColor: '#1976d2', progressColor: '#0b397e', cursorColor: '#9ca3af',
      barWidth: 2, barRadius: 2, normalize: true,
    });
    const regions = wave.registerPlugin(RegionsPlugin.create());
    wave.registerPlugin(HoverPlugin.create({
      lineColor: '#f3f4f6',
      lineWidth: 1,
      labelBackground: '#18181b',
      labelColor: '#f3f4f6',
      labelSize: '12px',
      formatTimeCallback: seconds => `${seconds.toFixed(3)} s`,
    }));
    waveRef.current = wave; regionsRef.current = regions;
    wave.on('ready', () => {
      const duration = videoRef.current?.duration || cacheEnd;
      wave.zoom(Math.max(1, 620 / duration));
      syncingRef.current = true;
      regions.addRegion({ id: 'analysis-range', start: range.start, end: range.end, drag: true, resize: true, color: 'rgba(25, 118, 210, 0.28)' });
      syncingRef.current = false;
    });
    regions.on('region-updated', region => {
      if (!syncingRef.current) setRange({ start: Number(region.start.toFixed(3)), end: Number(region.end.toFixed(3)) });
    });

    // Keep the waveform cursor and the displayed video on the same clock.
    // Clicking the waveform seeks the video; playing or seeking the video
    // moves the waveform progress indicator.
    wave.on('interaction', time => {
      if (videoRef.current) videoRef.current.currentTime = time;
    });
    const syncWaveformToVideo = () => {
      const video = videoRef.current;
      if (!video || !Number.isFinite(video.currentTime)) return;
      wave.setTime(video.currentTime);
    };
    videoRef.current.addEventListener('timeupdate', syncWaveformToVideo);
    videoRef.current.addEventListener('seeked', syncWaveformToVideo);

    return () => {
      videoRef.current?.removeEventListener('timeupdate', syncWaveformToVideo);
      videoRef.current?.removeEventListener('seeked', syncWaveformToVideo);
      wave.destroy();
      previewMedia.pause();
      previewMedia.removeAttribute('src');
      previewMedia.load();
    };
  }, [videoRef, cacheEnd]);

  const updateRange = (field, value) => {
    const next = { ...range, [field]: Number(value) };
    setRange(next);
    const region = regionsRef.current?.getRegions()?.find(item => item.id === 'analysis-range');
    if (region) { syncingRef.current = true; region.setOptions(next); syncingRef.current = false; }
  };

  return <div className="mt-3 rounded-lg border border-zinc-600 bg-zinc-700 p-3">
    <div className="mb-2 flex justify-between text-xs text-zinc-200">
      <span>Cached landmark range: {cacheStart.toFixed(3)}–{cacheEnd.toFixed(3)} s</span>
      <span className="text-zinc-300">Hover for exact time</span>
    </div>
    <div ref={waveformRef} className="overflow-x-auto rounded bg-zinc-800" />
    <div className="mt-3 flex flex-wrap items-end gap-3 text-sm text-gray-100">
      <label>Start <input className="ml-1 w-20 rounded border border-zinc-500 bg-zinc-800 p-1" type="number" step="0.001" min={cacheStart} max={range.end} value={range.start} onChange={e => updateRange('start', e.target.value)} /></label>
      <label>End <input className="ml-1 w-20 rounded border border-zinc-500 bg-zinc-800 p-1" type="number" step="0.001" min={range.start} max={cacheEnd} value={range.end} onChange={e => updateRange('end', e.target.value)} /></label>
      <label>Normalization <select className="ml-1 rounded border border-zinc-500 bg-zinc-800 p-1" value={strategy} onChange={e => setStrategy(e.target.value)}><option value="INDEXSIZE">Index finger size</option><option value="THUMBSIZE">Thumb size</option><option value="PALMSIZE">Palm size</option><option value="MAXAMPLITUDE">Max amplitude</option></select></label>
      <button className="rounded bg-[#1976d2] px-3 py-1 hover:bg-[#1565c0]" onClick={() => onApply(range, strategy)} disabled={range.start < cacheStart || range.end > cacheEnd || range.end <= range.start}>Apply from cached landmarks</button>
    </div>
  </div>;
};

export default AnalysisRangePanel;
