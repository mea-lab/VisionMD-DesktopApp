import { useEffect, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';
import RegionsPlugin from 'wavesurfer.js/plugins/regions';
import HoverPlugin from 'wavesurfer.js/plugins/hover';

/** Gait's WaveSurfer region editor shared by walking and single-rise tasks. */
export default function VideoSegmentsTimeline({ videoRef, start, end, regions,
  onRegionUpdated, previewSignal, previewStart = start, fps, disabled = false,
  label = 'Editable analysis intervals' }) {
  const containerRef = useRef(null);
  const waveRef = useRef(null);
  const pluginRef = useRef(null);
  const syncing = useRef(false);
  const current = useRef({ regions, onRegionUpdated, disabled });
  current.current = { regions, onRegionUpdated, disabled };
  const [error, setError] = useState('');
  const renderRegions = () => {
    const plugin = pluginRef.current;
    if (!plugin) return;
    syncing.current = true;
    plugin.clearRegions();
    for (const region of current.current.regions) {
      if (!Number.isFinite(region.start) || (region.end != null && !Number.isFinite(region.end))) continue;
      plugin.addRegion({ ...region,
        drag: !current.current.disabled && region.drag,
        resize: !current.current.disabled && region.resize });
    }
    syncing.current = false;
  };
  useEffect(() => {
    const video = videoRef?.current;
    if (!video || !containerRef.current || !(end > start)) return undefined;
    setError('');
    const preview = new Audio(video.currentSrc || video.src);
    const duration = Number.isFinite(video.duration) ? Math.max(end,video.duration) : end;
    // A pose preview supports silent videos, and is padded to absolute video
    // time so non-zero task starts never shift editable markers.
    let peaks;
    if (previewSignal?.length && fps > 0) {
      const channel = new Float32Array(Math.ceil(duration*fps)+1);
      const max = previewSignal.reduce((v,x) => Math.max(v,Math.abs(x || 0)),1e-8);
      previewSignal.forEach((value,i) => {
        const index = Math.round(previewStart*fps)+i;
        if (index >= 0 && index < channel.length) channel[index] = Number.isFinite(value) ? value/max : 0;
      });
      peaks = [channel];
    }
    const wave = WaveSurfer.create({ container: containerRef.current, media: preview,
      height: 82, waveColor: '#6b7280', progressColor: '#374151', cursorColor: '#111827',
      cursorWidth: 3, barWidth: 2, barRadius: 2, normalize: true,
      ...(peaks ? { peaks, duration } : {}) });
    const plugin = wave.registerPlugin(RegionsPlugin.create());
    wave.registerPlugin(HoverPlugin.create({ lineColor: '#111827', lineWidth: 1,
      labelBackground: '#18181b', labelColor: '#f3f4f6', labelSize: '12px',
      formatTimeCallback: seconds => `${seconds.toFixed(3)} s` }));
    waveRef.current = wave; pluginRef.current = plugin;
    wave.on('ready', () => { wave.zoom(Math.max(1,720/duration)); renderRegions(); });
    wave.on('error', reason => setError(reason.message || 'Timeline preview unavailable; use the time fields.'));
    plugin.on('region-update', region => { if (!syncing.current && !current.current.disabled) video.currentTime = region.start; });
    plugin.on('region-updated', region => {
      if (!syncing.current && !current.current.disabled) current.current.onRegionUpdated?.({ id: region.id, start: region.start, end: region.end });
    });
    wave.on('interaction', time => { video.currentTime = time; });
    const sync = () => { if (Number.isFinite(video.currentTime)) wave.setTime(video.currentTime); };
    video.addEventListener('timeupdate',sync); video.addEventListener('seeked',sync);
    return () => {
      video.removeEventListener('timeupdate',sync); video.removeEventListener('seeked',sync);
      wave.destroy(); preview.pause(); preview.removeAttribute('src'); preview.load();
      waveRef.current = null; pluginRef.current = null;
    };
  }, [videoRef, start, end, previewSignal, previewStart, fps]);
  useEffect(() => { renderRegions(); }, [regions, disabled]);
  return <div><div ref={containerRef} role="group" aria-label={label} className="overflow-x-auto rounded bg-zinc-800" />{error && <p role="alert" className="mt-2 text-sm text-orange-300">{error}</p>}</div>;
}
