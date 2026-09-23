import { r as reactExports, j as jsxRuntimeExports } from "./index-CcIK0TQJ.js";
import { U as UplotReact } from "./uPlot.min-BuVdl80p.js";
const TremorGraphs = ({ selectedTaskIndex, tasks, videoRef }) => {
  const task = tasks?.[selectedTaskIndex] ?? {};
  const signals = task.data?.signals ?? {};
  const start = task.start ?? 0;
  const end = task.end ?? 0;
  const names = Object.keys(signals);
  const [selectedName, setSelectedName] = reactExports.useState(() => names[0] ?? "");
  const maxAmp = Math.max(...Object.values(signals).flat().map(Math.abs));
  reactExports.useEffect(() => {
    if (!selectedName && names.length)
      setSelectedName(names[0]);
    else if (selectedName && !names.includes(selectedName))
      setSelectedName(names[0] ?? "");
  }, [names, selectedName]);
  const chartRef = reactExports.useRef(null);
  const time = reactExports.useMemo(() => {
    if (!selectedName) return [];
    const n = signals[selectedName]?.length ?? 0;
    const dt = n > 1 ? (end - start) / (n - 1) : 0;
    return Array.from({ length: n }, (_, i) => start + i * dt);
  }, [selectedName, start, end, signals]);
  const toggle = () => {
    const v = videoRef?.current;
    if (v) v.paused ? v.play() : v.pause();
  };
  const handleWheel = reactExports.useCallback((e) => {
    e.preventDefault();
    const u = chartRef.current;
    if (!u) return;
    const factor = e.deltaY < 0 ? 0.9 : 1.1;
    const { min, max } = u.scales.x;
    const center = (min + max) / 2;
    const range = (max - min) * factor;
    u.setScale("x", {
      min: center - range / 2,
      max: center + range / 2
    });
  }, []);
  reactExports.useEffect(() => {
    const vid = videoRef?.current;
    if (!vid || !selectedName) return;
    const step = () => {
      const c = chartRef.current;
      if (c) c.setCursor({ left: c.valToPos(vid.currentTime, "x") });
      vid.requestVideoFrameCallback(step);
    };
    vid.requestVideoFrameCallback(step);
  }, [videoRef, selectedName]);
  if (!selectedName) return null;
  const axisLabel = selectedName.split("_").map((w) => w[0].toUpperCase() + w.slice(1)).join(" ");
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-col gap-8 items-center mx-4", children: /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      className: "bg-[#333338] flex flex-col items-center rounded-lg p-4",
      onDoubleClick: toggle,
      onWheel: handleWheel,
      style: { position: "relative", overscrollBehavior: "contain", touchAction: "none" },
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "select",
          {
            value: selectedName,
            onChange: (e) => setSelectedName(e.target.value),
            className: "mb-4 bg-[#333338] text-gray-100 cursor-pointer",
            children: names.map((n) => {
              const lbl = n.split("_").map((w) => w[0].toUpperCase() + w.slice(1)).join(" ");
              return /* @__PURE__ */ jsxRuntimeExports.jsxs("option", { value: n, children: [
                lbl,
                " over Time"
              ] }, n);
            })
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          UplotReact,
          {
            options: {
              width: 600,
              height: 320,
              scales: {
                x: { time: false, min: start, max: end },
                y: { min: -maxAmp * 1.1, max: maxAmp * 1.1 }
              },
              legend: { show: false },
              axes: [
                {
                  label: "Time (s)",
                  values: (_, vals) => vals.map((v) => v.toFixed(2)),
                  grid: { show: true, color: "#9ca3af" },
                  ticks: { show: true },
                  stroke: "#9ca3af"
                },
                {
                  label: axisLabel,
                  grid: { show: true, color: "#9ca3af" },
                  ticks: { show: true },
                  stroke: "#9ca3af"
                }
              ],
              series: [
                {},
                { stroke: "#1f77b4", width: 2, points: { show: true, size: 4 } }
              ],
              cursor: { drag: { x: true }, x: true, y: false }
            },
            data: [time, signals[selectedName] ?? []],
            onCreate: (c) => {
              chartRef.current = c;
            },
            onDelete: () => {
              chartRef.current = null;
            }
          }
        )
      ]
    }
  ) });
};
export {
  TremorGraphs as T
};
