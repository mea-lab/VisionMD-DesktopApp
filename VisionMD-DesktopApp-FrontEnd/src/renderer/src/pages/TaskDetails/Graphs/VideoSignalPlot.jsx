import { useEffect, useMemo, useRef, useState } from 'react';
import UplotReact from 'uplot-react';
import 'uplot/dist/uPlot.min.css';

/** Shared gait/transition signal plot. Times are absolute video seconds. */
export default function VideoSignalPlot({ title, unit, axisLabel, time, series, videoRef,
  height = 320, markers = [], bands = [], threshold, peaks }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const [width, setWidth] = useState(600);
  useEffect(() => {
    if (!containerRef.current) return undefined;
    const observer = new ResizeObserver(entries => setWidth(Math.max(240, Math.floor(entries[0].contentRect.width))));
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    const video = videoRef?.current;
    if (!video) return undefined;
    let callback;
    let active = true;
    const sync = () => {
      const chart = chartRef.current;
      if (chart && Number.isFinite(video.currentTime)) {
        chart.setCursor({ left: chart.valToPos(video.currentTime, 'x') });
      }
    };
    const step = () => {
      if (!active) return;
      sync();
      callback = video.requestVideoFrameCallback(step);
    };
    video.addEventListener('timeupdate', sync);
    video.addEventListener('seeked', sync);
    if (video.requestVideoFrameCallback) callback = video.requestVideoFrameCallback(step);
    sync();
    return () => {
      active = false;
      video.removeEventListener('timeupdate', sync);
      video.removeEventListener('seeked', sync);
      if (callback !== undefined) video.cancelVideoFrameCallback?.(callback);
    };
  }, [videoRef, time]);
  const data = useMemo(() => [time, ...series.map(item => item.values)], [time, series]);
  const options = useMemo(() => ({
    width, height,
    scales: { x: { time: false, min: time[0], max: time.at(-1) } },
    legend: { show: series.length > 1 },
    axes: [
      { label: 'Time (s)', values: (_, values) => values.map(value => value.toFixed(2)), grid: { color: '#52525b' }, stroke: '#9ca3af' },
      { label: axisLabel || unit || title, size: 65, grid: { color: '#52525b' }, stroke: '#9ca3af' },
    ],
    series: [{}, ...series.map(item => ({ label: item.name, stroke: item.color || '#1f77b4', width: 2, points: { show: false } }))],
    cursor: { drag: { x: true }, x: true, y: false },
    hooks: {
      drawClear: [u => {
        const { ctx, bbox } = u;
        ctx.save();
        ctx.fillStyle = '#39393F';
        ctx.fillRect(bbox.left, bbox.top, bbox.width, bbox.height);
        ctx.beginPath(); ctx.rect(bbox.left, bbox.top, bbox.width, bbox.height); ctx.clip();
        for (const band of bands) {
          if (!Number.isFinite(band.start) || !Number.isFinite(band.end)) continue;
          ctx.fillStyle = band.color || 'rgba(96,165,250,.12)';
          const a = u.valToPos(band.start, 'x', true), b = u.valToPos(band.end, 'x', true);
          ctx.fillRect(a, bbox.top, Math.max(0, b-a), bbox.height);
        }
        ctx.restore();
      }],
      draw: [u => {
        const { ctx, bbox } = u;
        ctx.save(); ctx.beginPath(); ctx.rect(bbox.left, bbox.top, bbox.width, bbox.height); ctx.clip();
        const vertical = (value, color) => {
          const x = u.valToPos(value, 'x', true);
          ctx.strokeStyle = color; ctx.setLineDash([5,4]); ctx.beginPath(); ctx.moveTo(x,bbox.top); ctx.lineTo(x,bbox.top+bbox.height); ctx.stroke();
        };
        markers.forEach(item => { if (Number.isFinite(item.time)) vertical(item.time,item.color || '#d4d4d8'); });
        if (Number.isFinite(threshold)) {
          const y = u.valToPos(threshold,'y',true);
          ctx.strokeStyle = '#d4d4d8'; ctx.setLineDash([6,4]); ctx.beginPath(); ctx.moveTo(bbox.left,y); ctx.lineTo(bbox.left+bbox.width,y); ctx.stroke();
        }
        ctx.setLineDash([]); ctx.fillStyle = '#fb923c';
        peaks?.time?.forEach((t,i) => {
          if (!Number.isFinite(t) || !Number.isFinite(peaks.data[i])) return;
          ctx.beginPath(); ctx.arc(u.valToPos(t,'x',true),u.valToPos(peaks.data[i],'y',true),4,0,2*Math.PI); ctx.fill();
        });
        ctx.restore();
      }],
      ready: [u => {
        // A click seeks, while dragging continues to use uPlot's native zoom.
        let start;
        u.over.onpointerdown = event => { start = event.clientX; };
        u.over.onclick = event => {
          if (start != null && Math.abs(start-event.clientX) > 4) return;
          const video = videoRef?.current;
          if (!video) return;
          const t = u.posToVal(event.clientX-u.over.getBoundingClientRect().left,'x');
          video.currentTime = Math.max(time[0],Math.min(time.at(-1),t));
        };
      }],
    },
  }), [width, height, time, series, title, unit, axisLabel, markers, bands, threshold, peaks, videoRef]);
  if (time.length < 2 || !series.length) return null;
  return <div ref={containerRef} className="my-4 w-full min-w-0 overflow-hidden" onDoubleClick={() => {
    const video = videoRef?.current;
    if (video) { if (video.paused) video.play()?.catch(() => {}); else video.pause(); }
  }}>
    <h3 className="mb-2 font-medium text-gray-100">{title}</h3>
    {unit && <p className="mb-2 text-xs text-gray-300">{unit}</p>}
    <div role="img" aria-label={`${title} over time; ${unit || title}. Click to seek; drag to zoom.`}>
      <UplotReact options={options} data={data} onCreate={chart => { chartRef.current = chart; }} onDelete={() => { chartRef.current = null; }} />
    </div>
  </div>;
}
