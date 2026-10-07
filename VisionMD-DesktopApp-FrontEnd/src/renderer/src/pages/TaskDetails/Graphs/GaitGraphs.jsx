import { useMemo, useRef, useEffect, useState } from "react";
import UplotReact from "uplot-react";
import "uplot/dist/uPlot.min.css";

const formatSignalName = (name) => name
  .split("_")
  .map(word => word[0].toUpperCase() + word.slice(1))
  .join(" ");

const GaitGraphs = ({ selectedTaskIndex, tasks, videoRef }) => {
  const task    = tasks?.[selectedTaskIndex] ?? {};
  const signals = useMemo(() => task.data?.signals ?? {}, [task.data?.signals]);
  const start   = task.start ?? 0;
  const end     = task.end   ?? 0;
  const names = useMemo(() => Object.keys(signals), [signals]);

  const [selectedName, setSelectedName] = useState(() => names[0] ?? "");

  useEffect(() => {
    if (!selectedName && names.length)         setSelectedName(names[0]);
    else if (selectedName && !names.includes(selectedName))
                                               setSelectedName(names[0] ?? "");
  }, [names, selectedName]);

  const chartRef = useRef(null);

  const time = useMemo(() => {
    if (!selectedName) return [];
    const n = signals[selectedName]?.length ?? 0;
    const dt = n > 1 ? (end - start) / (n - 1) : 0;
    return Array.from({ length: n }, (_, i) => start + i * dt);
  }, [selectedName, start, end, signals]);

  const toggle = () => {
    const v = videoRef?.current;
    if (v) v.paused ? v.play() : v.pause();
  };

  useEffect(() => {
    const vid = videoRef?.current;
    if (!vid || !selectedName) return;

    let callbackId;
    let active = true;
    const step = () => {
      if (!active) return;
      const c = chartRef.current;
      if (c) c.setCursor({ left: c.valToPos(vid.currentTime, "x") });
      callbackId = vid.requestVideoFrameCallback(step);
    };
    callbackId = vid.requestVideoFrameCallback(step);
    return () => {
      active = false;
      if (callbackId !== undefined && vid.cancelVideoFrameCallback) {
        vid.cancelVideoFrameCallback(callbackId);
      }
    };
  }, [videoRef, selectedName]);

  if (!selectedName) return null;

  const axisLabel = formatSignalName(selectedName);

  return (
    <div className="flex flex-col gap-8 items-center mx-4">
      <div
        className="bg-[#333338] flex flex-col items-center rounded-lg p-4"
        onDoubleClick={toggle}
        style={{ position: "relative" }}
      >
        <select
          value={selectedName}
          onChange={e => setSelectedName(e.target.value)}
          className="mb-4 bg-[#333338] text-gray-100 cursor-pointer"
        >
          {names.map(n => {
            const lbl = formatSignalName(n);
            return <option key={n} value={n}>{lbl} over Time</option>;
          })}
        </select>

        <UplotReact
          options={{
            width: 600,
            height: 320,
            scales: { x: { time: false, min: start, max: end } },
            legend: { show: false },
            hooks: {
              drawClear: [
                (u) => {
                  const { left, top, width, height } = u.bbox;
                  const ctx = u.ctx;
                  ctx.save();
                  ctx.fillStyle = "#39393F";
                  ctx.fillRect(left - 15, top - 15, width + 30, height + 30);
                  ctx.restore();
                }
              ]
            },
            axes: [
              {
                label: "Time (s)",
                values: (_, vals) => vals.map(v => v.toFixed(2)),
                grid: { show: true, color: "#9ca3af" }, ticks: { show: true }, stroke: "#9ca3af",
              },
              {
                label: axisLabel,
                grid: { show: true, color: "#9ca3af" }, ticks: { show: true }, stroke: "#9ca3af",
              },
            ],
            series: [
              {},
              { stroke: "#1f77b4", width: 2, points: { show: true, size: 4 } },
            ],
            cursor: { drag: { x: true }, x: true, y: false}
          }}
          data={[time, signals[selectedName] ?? []]}
          onCreate={c => { chartRef.current = c; }}
          onDelete={() => { chartRef.current = null; }}
        />
      </div>
    </div>
  );
};

export default GaitGraphs;
