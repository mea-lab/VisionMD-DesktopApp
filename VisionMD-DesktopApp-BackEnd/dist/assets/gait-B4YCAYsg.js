import { r as reactExports, j as jsxRuntimeExports, w, d, l } from "./index-D5uQjtsf.js";
import "./react-plotly-BE7kqALW.js";
import { U as UplotReact, F as FeatureTable } from "./uPlot.min-J1lZBMnd.js";
const GaitGraphs = ({ selectedTaskIndex, tasks, videoRef }) => {
  const task = tasks?.[selectedTaskIndex] ?? {};
  const signals = task.data?.signals ?? {};
  const start = task.start ?? 0;
  const end = task.end ?? 0;
  const names = Object.keys(signals);
  const [selectedName, setSelectedName] = reactExports.useState(() => names[0] ?? "");
  reactExports.useEffect(() => {
    if (!selectedName && names.length) setSelectedName(names[0]);
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
  const axisLabel = selectedName.split("_").map((w2) => w2[0].toUpperCase() + w2.slice(1)).join(" ");
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-col gap-8 items-center mx-4", children: /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      className: "bg-[#333338] flex flex-col items-center rounded-lg p-4",
      onDoubleClick: toggle,
      style: { position: "relative" },
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "select",
          {
            value: selectedName,
            onChange: (e) => setSelectedName(e.target.value),
            className: "mb-4 bg-[#333338] text-gray-100 cursor-pointer",
            children: names.map((n) => {
              const lbl = n.split("_").map((w2) => w2[0].toUpperCase() + w2.slice(1)).join(" ");
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
const clamp = (value, minimum, maximum) => Math.min(maximum, Math.max(minimum, value));
const GaitSegmentsPanel = ({
  selectedTaskIndex,
  tasks,
  setTasks,
  videoRef
}) => {
  const task = tasks?.[selectedTaskIndex];
  const data = task?.data ?? {};
  const cache = data.gait_analysis_cache;
  const metadata = data.turning_metadata ?? {};
  const waveformRef = reactExports.useRef(null);
  const waveRef = reactExports.useRef(null);
  const regionsRef = reactExports.useRef(null);
  const previewMediaRef = reactExports.useRef(null);
  const syncingRef = reactExports.useRef(false);
  const fps = Number(cache?.fps || 0);
  const cacheStart = Number(cache?.start_time ?? task?.start ?? 0);
  const cachedFrames = cache?.poses3d?.length ?? 0;
  const cacheEnd = Number(
    cachedFrames > 1 && fps > 0 ? cacheStart + (cachedFrames - 1) / fps : task?.end ?? cacheStart
  );
  const detectedRange = reactExports.useMemo(() => {
    if (metadata.is_turning) {
      return {
        start: Number(metadata.start_time_seconds),
        end: Number(metadata.end_time_seconds)
      };
    }
    const middle = (cacheStart + cacheEnd) / 2;
    const halfWidth = Math.min(0.5, (cacheEnd - cacheStart) / 10);
    return { start: middle - halfWidth, end: middle + halfWidth };
  }, [metadata.is_turning, metadata.start_time_seconds, metadata.end_time_seconds, cacheStart, cacheEnd]);
  const [expanded, setExpanded] = reactExports.useState(true);
  const [hasTurn, setHasTurn] = reactExports.useState(Boolean(metadata.is_turning));
  const [turnRange, setTurnRange] = reactExports.useState(detectedRange);
  const [applying, setApplying] = reactExports.useState(false);
  const [error, setError] = reactExports.useState("");
  reactExports.useEffect(() => {
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
        id: "walking-all",
        start: cacheStart,
        end: cacheEnd,
        drag: false,
        resize: false,
        color: "rgba(37, 99, 235, 0.30)"
      });
    } else {
      const start = clamp(range.start, cacheStart, cacheEnd);
      const end = clamp(range.end, start, cacheEnd);
      if (start > cacheStart) {
        regions.addRegion({
          id: "walking-before",
          start: cacheStart,
          end: start,
          drag: false,
          resize: false,
          color: "rgba(37, 99, 235, 0.30)"
        });
      }
      regions.addRegion({
        id: "turn",
        start,
        end,
        drag: true,
        resize: true,
        color: "rgba(239, 68, 68, 0.42)"
      });
      if (end < cacheEnd) {
        regions.addRegion({
          id: "walking-after",
          start: end,
          end: cacheEnd,
          drag: false,
          resize: false,
          color: "rgba(34, 197, 94, 0.28)"
        });
      }
    }
    syncingRef.current = false;
  };
  reactExports.useEffect(() => {
    if (!expanded || !videoRef.current || !waveformRef.current || cacheEnd <= cacheStart) return;
    const previewMedia = new Audio(videoRef.current.currentSrc || videoRef.current.src);
    previewMediaRef.current = previewMedia;
    const wave = w.create({
      container: waveformRef.current,
      media: previewMedia,
      height: 82,
      waveColor: "#6b7280",
      progressColor: "#374151",
      cursorColor: "#f3f4f6",
      barWidth: 2,
      barRadius: 2,
      normalize: true
    });
    const regions = wave.registerPlugin(d.create());
    wave.registerPlugin(l.create({
      lineColor: "#f3f4f6",
      lineWidth: 1,
      labelBackground: "#18181b",
      labelColor: "#f3f4f6",
      labelSize: "12px",
      formatTimeCallback: (seconds) => `${seconds.toFixed(3)} s`
    }));
    waveRef.current = wave;
    regionsRef.current = regions;
    wave.on("ready", () => {
      const duration = videoRef.current?.duration || cacheEnd;
      wave.zoom(Math.max(1, 720 / duration));
      renderRegions(Boolean(metadata.is_turning), detectedRange);
    });
    regions.on("region-updated", (region) => {
      if (syncingRef.current || region.id !== "turn") return;
      const next = {
        start: Number(region.start.toFixed(3)),
        end: Number(region.end.toFixed(3))
      };
      setTurnRange(next);
      renderRegions(true, next);
    });
    wave.on("interaction", (time) => {
      if (videoRef.current) videoRef.current.currentTime = time;
    });
    const syncToVideo = () => {
      if (Number.isFinite(videoRef.current?.currentTime)) {
        wave.setTime(videoRef.current.currentTime);
      }
    };
    videoRef.current.addEventListener("timeupdate", syncToVideo);
    videoRef.current.addEventListener("seeked", syncToVideo);
    return () => {
      videoRef.current?.removeEventListener("timeupdate", syncToVideo);
      videoRef.current?.removeEventListener("seeked", syncToVideo);
      wave.destroy();
      previewMedia.pause();
      previewMedia.removeAttribute("src");
      previewMedia.load();
      waveRef.current = null;
      regionsRef.current = null;
    };
  }, [expanded, videoRef, cacheStart, cacheEnd]);
  reactExports.useEffect(() => {
    if (waveRef.current) renderRegions(hasTurn, turnRange);
  }, [hasTurn]);
  const updateBoundary = (field, rawValue) => {
    const value = Number(rawValue);
    const next = {
      ...turnRange,
      [field]: value
    };
    setTurnRange(next);
    renderRegions(hasTurn, next);
  };
  const applySegments = async () => {
    setApplying(true);
    setError("");
    try {
      const form = new FormData();
      form.append("json_data", JSON.stringify({
        task_data: data,
        turning_segment: {
          is_turning: hasTurn,
          start_time_seconds: turnRange.start,
          end_time_seconds: turnRange.end
        }
      }));
      const response = await fetch("http://localhost:8000/api/update_gait_segments/", {
        method: "POST",
        body: form
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || `Server returned ${response.status}`);
      setTasks((previous) => previous.map(
        (item, index) => index === selectedTaskIndex ? { ...item, data: result } : item
      ));
    } catch (reason) {
      setError(reason.message || "Could not update gait segments.");
    } finally {
      setApplying(false);
    }
  };
  const invalidRange = hasTurn && (turnRange.start < cacheStart || turnRange.end > cacheEnd || turnRange.end <= turnRange.start);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-6 rounded-lg border border-zinc-600 bg-zinc-700", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "button",
      {
        type: "button",
        className: "w-full px-4 py-2 text-left font-semibold hover:bg-zinc-600",
        onClick: () => setExpanded((value) => !value),
        children: [
          expanded ? "▾" : "▸",
          " Walking & turning segments"
        ]
      }
    ),
    expanded && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border-t border-zinc-600 p-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-2 flex flex-wrap items-center justify-between gap-2 text-xs text-zinc-200", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
          "Cached gait range: ",
          cacheStart.toFixed(3),
          "–",
          cacheEnd.toFixed(3),
          " s"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: "Hover for exact time; click to seek the video" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: waveformRef, className: "overflow-x-auto rounded bg-zinc-800" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-2 flex flex-wrap gap-4 text-xs", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: "mr-1 inline-block h-3 w-3 bg-blue-600/70" }),
          "Walking segment 1"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: "mr-1 inline-block h-3 w-3 bg-red-500/70" }),
          "Turn"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: "mr-1 inline-block h-3 w-3 bg-green-500/70" }),
          "Walking segment 2"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-3 flex flex-wrap items-end gap-3 text-sm", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { className: "flex items-center gap-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "checkbox",
              checked: hasTurn,
              onChange: (event) => {
                const enabled = event.target.checked;
                if (enabled && turnRange.end <= turnRange.start) {
                  const middle = (cacheStart + cacheEnd) / 2;
                  const halfWidth = Math.min(0.5, (cacheEnd - cacheStart) / 10);
                  setTurnRange({ start: middle - halfWidth, end: middle + halfWidth });
                }
                setHasTurn(enabled);
              }
            }
          ),
          "Turn present"
        ] }),
        hasTurn && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { children: [
            "Turn start ",
            /* @__PURE__ */ jsxRuntimeExports.jsx("input", { className: "ml-1 w-24 rounded border border-zinc-500 bg-zinc-800 p-1", type: "number", step: "0.001", min: cacheStart, max: turnRange.end, value: turnRange.start, onChange: (event) => updateBoundary("start", event.target.value) })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { children: [
            "Turn end ",
            /* @__PURE__ */ jsxRuntimeExports.jsx("input", { className: "ml-1 w-24 rounded border border-zinc-500 bg-zinc-800 p-1", type: "number", step: "0.001", min: turnRange.start, max: cacheEnd, value: turnRange.end, onChange: (event) => updateBoundary("end", event.target.value) })
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            type: "button",
            className: "rounded bg-[#1976d2] px-3 py-1 hover:bg-[#1565c0] disabled:cursor-not-allowed disabled:opacity-50",
            disabled: !cache || applying || invalidRange,
            onClick: applySegments,
            children: applying ? "Recalculating…" : "Apply from cached gait landmarks"
          }
        )
      ] }),
      !cache && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-2 text-sm text-amber-300", children: "This older JSON can display its detected segments, but it does not contain the cached gait data required to edit them." }),
      error && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-2 text-sm text-red-400", children: error })
    ] })
  ] });
};
const Gait = ({
  selectedTaskIndex,
  tasks,
  setTasks,
  fileName,
  videoRef,
  startTime,
  endTime,
  handleJSONUpload
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: tasks[selectedTaskIndex] && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      GaitSegmentsPanel,
      {
        selectedTaskIndex,
        tasks,
        setTasks,
        videoRef
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      GaitGraphs,
      {
        selectedTaskIndex,
        tasks,
        fileName,
        videoRef,
        startTime,
        endTime
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      FeatureTable,
      {
        selectedTaskIndex,
        tasks,
        fileName
      }
    )
  ] }) });
};
export {
  Gait as default
};
