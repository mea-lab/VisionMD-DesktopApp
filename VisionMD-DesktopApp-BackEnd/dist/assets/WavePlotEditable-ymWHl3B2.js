import { r as reactExports, j as jsxRuntimeExports, B as Button, a as default_1, w, d, l, u as useTheme } from "./index-CcIK0TQJ.js";
import { P as Plot } from "./react-plotly-5EjayYNa.js";
const ScatterPlot = ({ tasks, selectedTaskIndex, fileName }) => {
  const currentTask = tasks[selectedTaskIndex];
  const { radarTable } = currentTask.data;
  const currentTaskName = currentTask.name;
  const [plotlyData, setPlotlyData] = reactExports.useState([]);
  const [plotlyLayout, setPlotlyLayout] = reactExports.useState({});
  const [plotlyConfig, setPlotlyConfig] = reactExports.useState({});
  const [tableView, setTableView] = reactExports.useState(true);
  reactExports.useEffect(() => {
    const features = Object.keys(radarTable);
    const values = Object.values(radarTable);
    setPlotlyData([
      {
        type: "scatterpolar",
        r: values,
        theta: features,
        fill: "toself",
        name: currentTaskName
      }
    ]);
    setPlotlyLayout({
      polar: {
        radialaxis: { visible: true, autorange: true, tickfont: { color: "#f3f4f6" } },
        angularaxis: { tickfont: { color: "#f3f4f6" } }
      },
      showlegend: false,
      autosize: false,
      height: 600,
      width: 600,
      plot_bgcolor: "transparent",
      paper_bgcolor: "transparent",
      font: { size: 7 },
      automargin: true
    });
    setPlotlyConfig({
      modeBarButtonsToRemove: ["zoom2d", "select2d", "lasso2d", "resetScale2d"],
      responsive: true,
      displaylogo: false,
      toImageButtonOptions: {
        filename: (fileName ? fileName.replace(/\.[^/.]+$/, "") : currentTaskName) + "_radarPlot"
      }
    });
  }, [radarTable, currentTaskName, fileName]);
  const showTable = () => setTableView(true);
  const showPlot = () => setTableView(false);
  const downloadCSV = () => {
    let csv = "data:text/csv;charset=utf-8,Feature,Value\r\n";
    Object.entries(radarTable).forEach(([feat, val]) => {
      csv += `${feat},${typeof val === "number" ? val.toFixed(6) : val}\r
`;
    });
    const encoded = encodeURI(csv);
    const a = document.createElement("a");
    a.href = encoded;
    a.download = `${fileName ? fileName.replace(/\.[^/.]+$/, "") : currentTaskName}_${currentTaskName}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { style: { position: "relative" }, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex p-4 space-x-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          className: `px-4 py-2 text-sm font-semibold rounded-md ${tableView ? "bg-[#1976d2] hover:bg-[#1565c0] text-white" : "bg-gray-200 text-gray-800"}`,
          onClick: showTable,
          children: "Table"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          className: `px-4 py-2 text-sm font-semibold rounded-md ${!tableView ? "bg-[#1976d2] hover:bg-[#1565c0] text-white" : "bg-gray-200 text-gray-800"}`,
          onClick: showPlot,
          children: "Scatter Plot"
        }
      )
    ] }),
    tableView ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto bg-[#333338] rounded-lg shadow-lg", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "min-w-full divide-y divide-zinc-200", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { className: "", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-6 py-3 text-left text-xs font-medium text-gray-100 uppercase tracking-wider", children: "Feature" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-6 py-3 text-left text-xs font-medium text-gray-100 uppercase tracking-wider", children: "Value" })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-zinc-600", children: Object.entries(radarTable).map(([feat, val]) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-200", children: feat }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-6 py-4 whitespace-nowrap text-sm text-gray-400", children: typeof val === "number" ? val.toFixed(4) : val })
        ] }, feat)) })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-4 flex justify-center", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        Button,
        {
          variant: "contained",
          onClick: downloadCSV,
          startIcon: /* @__PURE__ */ jsxRuntimeExports.jsx(default_1, {}),
          sx: {
            textTransform: "none",
            fontWeight: "bold",
            px: 3,
            py: 1
          },
          children: "Download CSV"
        }
      ) })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex justify-center", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Plot, { data: plotlyData, layout: plotlyLayout, config: plotlyConfig }) })
  ] });
};
const AnalysisRangePanel = ({ videoRef, cacheStart, cacheEnd, start, end, normStrategy, onApply }) => {
  const waveformRef = reactExports.useRef(null);
  const waveRef = reactExports.useRef(null);
  const regionsRef = reactExports.useRef(null);
  const previewMediaRef = reactExports.useRef(null);
  const syncingRef = reactExports.useRef(false);
  const [range, setRange] = reactExports.useState({ start, end });
  const [strategy, setStrategy] = reactExports.useState(normStrategy || "INDEXSIZE");
  reactExports.useEffect(() => setRange({ start, end }), [start, end]);
  reactExports.useEffect(() => setStrategy(normStrategy || "INDEXSIZE"), [normStrategy]);
  reactExports.useEffect(() => {
    if (!videoRef.current || !waveformRef.current) return;
    const previewMedia = new Audio(videoRef.current.currentSrc || videoRef.current.src);
    previewMediaRef.current = previewMedia;
    const wave = w.create({
      container: waveformRef.current,
      media: previewMedia,
      height: 76,
      waveColor: "#1976d2",
      progressColor: "#0b397e",
      cursorColor: "#9ca3af",
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
      wave.zoom(Math.max(1, 620 / duration));
      syncingRef.current = true;
      regions.addRegion({ id: "analysis-range", start: range.start, end: range.end, drag: true, resize: true, color: "rgba(25, 118, 210, 0.28)" });
      syncingRef.current = false;
    });
    regions.on("region-updated", (region) => {
      if (!syncingRef.current) setRange({ start: Number(region.start.toFixed(3)), end: Number(region.end.toFixed(3)) });
    });
    wave.on("interaction", (time) => {
      if (videoRef.current) videoRef.current.currentTime = time;
    });
    const syncWaveformToVideo = () => {
      const video = videoRef.current;
      if (!video || !Number.isFinite(video.currentTime)) return;
      wave.setTime(video.currentTime);
    };
    videoRef.current.addEventListener("timeupdate", syncWaveformToVideo);
    videoRef.current.addEventListener("seeked", syncWaveformToVideo);
    return () => {
      videoRef.current?.removeEventListener("timeupdate", syncWaveformToVideo);
      videoRef.current?.removeEventListener("seeked", syncWaveformToVideo);
      wave.destroy();
      previewMedia.pause();
      previewMedia.removeAttribute("src");
      previewMedia.load();
    };
  }, [videoRef, cacheEnd]);
  const updateRange = (field, value) => {
    const next = { ...range, [field]: Number(value) };
    setRange(next);
    const region = regionsRef.current?.getRegions()?.find((item) => item.id === "analysis-range");
    if (region) {
      syncingRef.current = true;
      region.setOptions(next);
      syncingRef.current = false;
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-3 rounded-lg border border-zinc-600 bg-zinc-700 p-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-2 flex justify-between text-xs text-zinc-200", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
        "Cached landmark range: ",
        cacheStart.toFixed(3),
        "–",
        cacheEnd.toFixed(3),
        " s"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-zinc-300", children: "Hover for exact time" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: waveformRef, className: "overflow-x-auto rounded bg-zinc-800" }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-3 flex flex-wrap items-end gap-3 text-sm text-gray-100", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { children: [
        "Start ",
        /* @__PURE__ */ jsxRuntimeExports.jsx("input", { className: "ml-1 w-20 rounded border border-zinc-500 bg-zinc-800 p-1", type: "number", step: "0.001", min: cacheStart, max: range.end, value: range.start, onChange: (e) => updateRange("start", e.target.value) })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { children: [
        "End ",
        /* @__PURE__ */ jsxRuntimeExports.jsx("input", { className: "ml-1 w-20 rounded border border-zinc-500 bg-zinc-800 p-1", type: "number", step: "0.001", min: range.start, max: cacheEnd, value: range.end, onChange: (e) => updateRange("end", e.target.value) })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { children: [
        "Normalization ",
        /* @__PURE__ */ jsxRuntimeExports.jsxs("select", { className: "ml-1 rounded border border-zinc-500 bg-zinc-800 p-1", value: strategy, onChange: (e) => setStrategy(e.target.value), children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "INDEXSIZE", children: "Index finger size" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "THUMBSIZE", children: "Thumb size" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "PALMSIZE", children: "Palm size" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "MAXAMPLITUDE", children: "Max amplitude" })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { className: "rounded bg-[#1976d2] px-3 py-1 hover:bg-[#1565c0]", onClick: () => onApply(range, strategy), disabled: range.start < cacheStart || range.end > cacheEnd || range.end <= range.start, children: "Apply from cached landmarks" })
    ] })
  ] });
};
const WavePlotEditable = ({
  selectedTaskIndex,
  tasks,
  setTasks,
  videoRef,
  startTime,
  endTime,
  handleJSONUpload
}) => {
  const { theme } = useTheme();
  const light = theme === "light";
  const [currentData, setCurrentData] = reactExports.useState(tasks?.[selectedTaskIndex]?.data);
  reactExports.useEffect(() => {
    setCurrentData(tasks[selectedTaskIndex].data);
    setDataRevision((r) => r + 1);
  }, [tasks?.[selectedTaskIndex]?.data, selectedTaskIndex]);
  const [videoCurrentTime, setVideoCurrentTime] = reactExports.useState(startTime);
  const [blurEnd, setBlurEnd] = reactExports.useState(startTime);
  const [blurStart, setBlurStart] = reactExports.useState(endTime);
  const [popup, setPopup] = reactExports.useState({ msg: "", show: false });
  const [alertPopup, setAlertPopup] = reactExports.useState({ msg: "", show: false });
  const [taskFlags, setTaskFlags] = reactExports.useState({ addNew: false, remove: false });
  const [addPointName, setAddPointName] = reactExports.useState("valley_start");
  const [isMarkUp, setIsMarkUp] = reactExports.useState(false);
  const [tempCycle, setTempCycle] = reactExports.useState({
    valleyStart: null,
    peak: null
  });
  const [dataRevision, setDataRevision] = reactExports.useState(0);
  const [uiRevision, setUiRevision] = reactExports.useState("stable");
  const [quickAdd, setQuickAdd] = reactExports.useState({
    peakHigh: false,
    peakLowStart: false,
    peakLowEnd: false
  });
  const [selectedPoint, setSelectedPoint] = reactExports.useState({});
  const [isKeyDown, setIsKeyDown] = reactExports.useState(false);
  const [showAnalysisRange, setShowAnalysisRange] = reactExports.useState(false);
  const [reanalysing, setReanalysing] = reactExports.useState(false);
  const [rangeError, setRangeError] = reactExports.useState("");
  const plotRef = reactExports.useRef(null);
  const updateCurrentTaskData = (updatedData) => {
    const updatedTasks = [...tasks];
    updatedTasks[selectedTaskIndex] = {
      ...updatedTasks[selectedTaskIndex],
      data: updatedData
    };
    setTasks(updatedTasks);
  };
  const applyCachedAnalysisRange = async (range, normStrategy) => {
    const task = tasks[selectedTaskIndex];
    const cache = currentData.analysis_cache || {
      start_time: task.start,
      end_time: task.end,
      // Older VisionMD JSON files did not persist cache metadata.  Landmark
      // arrays contain one entry per source video frame, so derive the source
      // FPS for backward-compatible cached re-analysis.
      fps: currentData.landMarks?.length / Math.max(task.end - task.start, Number.EPSILON),
      landmark_start_frame: currentData.landmark_start_frame,
      landMarks: currentData.landMarks,
      allLandMarks: currentData.allLandMarks
    };
    setReanalysing(true);
    setRangeError("");
    try {
      const form = new FormData();
      form.append("json_data", JSON.stringify({
        task_name: task.name,
        start_time: range.start,
        end_time: range.end,
        fps: cache.fps,
        norm_strategy: normStrategy,
        analysis_cache: cache
      }));
      const response = await fetch("http://localhost:8000/api/update_landmarks/", { method: "POST", body: form });
      if (!response.ok) throw new Error(await response.text());
      const data = await response.json();
      setTasks((previous) => previous.map((item, index) => index === selectedTaskIndex ? { ...item, start: range.start, end: range.end, norm_strategy: normStrategy, data } : item));
      setShowAnalysisRange(false);
    } catch (error) {
      setRangeError(error.message || "Could not re-analyze from cached landmarks.");
    } finally {
      setReanalysing(false);
    }
  };
  reactExports.useEffect(() => {
    const videoEl = videoRef.current;
    let frameId = null;
    const updateFrame = () => {
      if (!videoEl.paused && !videoEl.ended) {
        setVideoCurrentTime(videoEl.currentTime);
        frameId = requestAnimationFrame(updateFrame);
      }
    };
    const playHandler = () => {
      if (!frameId) frameId = requestAnimationFrame(updateFrame);
    };
    const pauseHandler = () => {
      if (frameId) {
        cancelAnimationFrame(frameId);
        frameId = null;
      }
      setVideoCurrentTime(videoEl.currentTime);
    };
    const timeUpdateHandler = () => {
      setVideoCurrentTime(videoEl.currentTime);
    };
    videoEl.addEventListener("play", playHandler);
    videoEl.addEventListener("pause", pauseHandler);
    videoEl.addEventListener("ended", pauseHandler);
    videoEl.addEventListener("timeupdate", timeUpdateHandler);
    return () => {
      videoEl.removeEventListener("play", playHandler);
      videoEl.removeEventListener("pause", pauseHandler);
      videoEl.removeEventListener("ended", pauseHandler);
      videoEl.removeEventListener("timeupdate", timeUpdateHandler);
      if (frameId) cancelAnimationFrame(frameId);
    };
  }, [videoRef]);
  reactExports.useEffect(() => {
    const keyDownHandler = (evt) => {
      if (!isKeyDown) {
        setIsKeyDown(true);
        if (evt.code === "Escape") cancelCurrentTask();
        else if (evt.code === "KeyQ")
          setQuickAdd((q) => ({ ...q, peakHigh: true }));
        else if (evt.code === "KeyW")
          setQuickAdd((q) => ({ ...q, peakLowStart: true }));
        else if (evt.code === "KeyE")
          setQuickAdd((q) => ({ ...q, peakLowEnd: true }));
      }
    };
    const keyUpHandler = (evt) => {
      setIsKeyDown(false);
      if (evt.code === "KeyQ")
        setQuickAdd((q) => ({ ...q, peakHigh: false }));
      if (evt.code === "KeyW")
        setQuickAdd((q) => ({ ...q, peakLowStart: false }));
      if (evt.code === "KeyE")
        setQuickAdd((q) => ({ ...q, peakLowEnd: false }));
    };
    document.addEventListener("keydown", keyDownHandler);
    document.addEventListener("keyup", keyUpHandler);
    return () => {
      document.removeEventListener("keydown", keyDownHandler);
      document.removeEventListener("keyup", keyUpHandler);
    };
  }, [isKeyDown]);
  const cancelCurrentTask = () => {
    setPopup({ msg: "", show: false });
    setAlertPopup({ msg: "", show: false });
    setTaskFlags({ addNew: false, remove: false });
    setSelectedPoint({});
    setAddPointName("valley_start");
    setTempCycle({ valleyStart: null, peak: null });
    resetBlur();
  };
  const resetBlur = () => {
    setBlurEnd(startTime);
    setBlurStart(endTime);
  };
  const showPopUp = (msg) => setPopup({ msg, show: true });
  const isInAnyExistingCycle = (x) => {
    const starts = currentData.valleys_start.time;
    const ends = currentData.valleys_end.time;
    return starts.some((s, i) => x >= s && x <= ends[i]);
  };
  const intervalsOverlap = (aStart, aEnd, bStart, bEnd) => {
    return aStart < bEnd && bStart < aEnd;
  };
  const isOverlappingExistingCycle = (newStart, newEnd) => {
    const starts = currentData.valleys_start.time;
    const ends = currentData.valleys_end.time;
    for (let i = 0; i < starts.length; i++) {
      if (intervalsOverlap(newStart, newEnd, starts[i], ends[i])) {
        return true;
      }
    }
    return false;
  };
  const handleClickOnPlot = (plotClickData) => {
    const { x, y, data: plotSeries } = plotClickData.points[0];
    videoRef.current.currentTime = x;
    videoRef.current.pause();
    if (quickAdd.peakHigh || quickAdd.peakLowStart || quickAdd.peakLowEnd) {
      handleQuickAdd(x, y);
      return;
    }
    if (!isMarkUp && taskFlags.addNew) {
      addNewPeakAndValley({ x, y });
      return;
    }
    if (!isMarkUp && taskFlags.remove) {
      const name = plotSeries.name;
      if (["Peak values", "Valley start", "Valley end"].includes(name)) {
        const idx = findIndexForClickedPoint(name, x, y);
        if (idx !== -1) {
          setSelectedPoint({ idx, name });
          setPopup({ msg: "", show: false });
          setAlertPopup({
            msg: "All points in this cycle will be removed. Are you sure?",
            show: true
          });
        }
      }
      return;
    }
    if (!isMarkUp) {
      const name = plotSeries.name;
      if (["peak values", "valley start", "valley end"].includes(name)) {
        const found = handleSelectElementFromArray(name, x);
        if (found) setSelectedPoint(found);
      }
      setDataRevision((r) => r + 1);
    } else if (isMarkUp && selectedPoint.name === "peak values") {
      const idx = selectedPoint.idx;
      if (x > currentData.valleys_start.time[idx] && x < currentData.valleys_end.time[idx]) {
        const newPeaks = {
          data: currentData.peaks.data.map((d2, i) => i === idx ? y : d2),
          time: currentData.peaks.time.map((t, i) => i === idx ? x : t)
        };
        updateCurrentTaskData({ ...currentData, peaks: newPeaks });
        setSelectedPoint({});
        resetBlur();
        setIsMarkUp(false);
        setDataRevision((r) => r + 1);
      } else {
        showPopUp("Peak must lie within the valley start/end range.");
      }
    }
  };
  const addNewPeakAndValley = ({ x, y }) => {
    if (addPointName === "valley_start") {
      if (isInAnyExistingCycle(x)) {
        showPopUp("You are trying to place a valley start that overlaps another cycle.");
        return;
      }
      setTempCycle({ valleyStart: { x, y }, peak: null });
      setAddPointName("peak");
      showPopUp("Next, select the new peak point.");
      setDataRevision((r) => r + 1);
    } else if (addPointName === "peak") {
      if (!tempCycle.valleyStart) {
        showPopUp("No valley start found. Please cancel and try again.");
        return;
      }
      if (x <= tempCycle.valleyStart.x) {
        showPopUp("Peak time must be after the Valley Start time.");
        return;
      }
      if (isOverlappingExistingCycle(tempCycle.valleyStart.x, x)) {
        showPopUp("Peak is overlapping with an existing cycle range.");
        return;
      }
      setTempCycle((prev) => ({ ...prev, peak: { x, y } }));
      setAddPointName("valley_end");
      showPopUp("Finally, select the new valley end point.");
      setDataRevision((r) => r + 1);
    } else if (addPointName === "valley_end") {
      if (!tempCycle.valleyStart || !tempCycle.peak) {
        showPopUp("No valley start or peak found. Please cancel and try again.");
        return;
      }
      if (x <= tempCycle.peak.x) {
        showPopUp("Valley end time must be after the Peak time.");
        return;
      }
      if (isOverlappingExistingCycle(tempCycle.peak.x, x)) {
        showPopUp("Valley end is overlapping with an existing cycle range.");
        return;
      }
      const newValleysStart = {
        data: [...currentData.valleys_start.data, tempCycle.valleyStart.y],
        time: [...currentData.valleys_start.time, tempCycle.valleyStart.x]
      };
      const newPeaks = {
        data: [...currentData.peaks.data, tempCycle.peak.y],
        time: [...currentData.peaks.time, tempCycle.peak.x]
      };
      const newValleysEnd = {
        data: [...currentData.valleys_end.data, y],
        time: [...currentData.valleys_end.time, x]
      };
      const updatedData = {
        ...currentData,
        valleys_start: newValleysStart,
        peaks: newPeaks,
        valleys_end: newValleysEnd
      };
      updateCurrentTaskData(updatedData);
      updateRadarTable(updatedData);
      handleJSONUpload(true, updatedData);
      cancelCurrentTask();
      setDataRevision((r) => r + 1);
    }
  };
  const removePeakAndValley = () => {
    const idx = selectedPoint.idx;
    if (idx < 0 || idx >= currentData.peaks.data.length) return;
    const newPeaks = {
      data: currentData.peaks.data.filter((_, i) => i !== idx),
      time: currentData.peaks.time.filter((_, i) => i !== idx)
    };
    const newValleyStart = {
      data: currentData.valleys_start.data.filter((_, i) => i !== idx),
      time: currentData.valleys_start.time.filter((_, i) => i !== idx)
    };
    const newValleyEnd = {
      data: currentData.valleys_end.data.filter((_, i) => i !== idx),
      time: currentData.valleys_end.time.filter((_, i) => i !== idx)
    };
    const updatedData = {
      ...currentData,
      peaks: newPeaks,
      valleys_start: newValleyStart,
      valleys_end: newValleyEnd
    };
    updateCurrentTaskData(updatedData);
    handleJSONUpload(true, updatedData);
    updateRadarTable(updatedData);
    cancelCurrentTask();
    setDataRevision((r) => r + 1);
  };
  const continueAlert = () => {
    setAlertPopup({ msg: "", show: false });
    removePeakAndValley();
  };
  const handleQuickAdd = (x, y) => {
    const dataCopy = { ...currentData };
    if (quickAdd.peakHigh) {
      dataCopy.peaks.data.push(y);
      dataCopy.peaks.time.push(x);
      setQuickAdd((q) => ({ ...q, peakHigh: false }));
    } else if (quickAdd.peakLowStart) {
      dataCopy.valleys_start.data.push(y);
      dataCopy.valleys_start.time.push(x);
      setQuickAdd((q) => ({ ...q, peakLowStart: false }));
    } else if (quickAdd.peakLowEnd) {
      dataCopy.valleys_end.data.push(y);
      dataCopy.valleys_end.time.push(x);
      setQuickAdd((q) => ({ ...q, peakLowEnd: false }));
    }
    updateCurrentTaskData(dataCopy);
    setDataRevision((r) => r + 1);
    updateRadarTable(dataCopy);
  };
  const getPointArrays = (name) => {
    if (name === "Peak values") return currentData.peaks;
    if (name === "Valley start") return currentData.valleys_start;
    if (name === "Valley end") return currentData.valleys_end;
    return { data: [], time: [] };
  };
  const findIndexForClickedPoint = (name, xVal, yVal) => {
    const { data, time } = getPointArrays(name);
    const idx = time.indexOf(xVal);
    return idx !== -1 && data[idx] === yVal ? idx : -1;
  };
  const handleSelectElementFromArray = (name, xVal) => {
    const { data, time } = getPointArrays(name);
    const idx = time.indexOf(xVal);
    if (idx >= 0) {
      setIsMarkUp(true);
      if (name === "peak values") {
        setBlurEnd(currentData.valleys_start.time[idx]);
        setBlurStart(currentData.valleys_end.time[idx]);
      }
      return { peak_data: [data[idx]], peak_time: [time[idx]], idx, name };
    }
    return null;
  };
  const updateRadarTable = async (dataToUse = null) => {
    try {
      const dataForUpdate = dataToUse || currentData;
      const jsonData = JSON.stringify({
        peaks_Data: dataForUpdate.peaks.data,
        peaks_Time: dataForUpdate.peaks.time,
        valleys_StartData: dataForUpdate.valleys_start.data,
        valleys_StartTime: dataForUpdate.valleys_start.time,
        valleys_EndData: dataForUpdate.valleys_end.data,
        valleys_EndTime: dataForUpdate.valleys_end.time,
        velocity_Data: dataForUpdate.velocityPlot.data,
        velocity_Time: dataForUpdate.velocityPlot.time
      });
      const uploadData = new FormData();
      uploadData.append("json_data", jsonData);
      const response = await fetch("http://localhost:8000/api/update_plot/", {
        method: "POST",
        body: uploadData
      });
      if (response.ok) {
        const data = await response.json();
        const newJsonData = {
          ...dataForUpdate,
          radarTable: data
        };
        updateCurrentTaskData(newJsonData);
        handleJSONUpload(true, newJsonData);
      } else {
        throw new Error("Server responded with an error!");
      }
    } catch (error) {
      console.error("Failed to update plot data:", error);
    }
  };
  const shapes = [
    {
      type: "line",
      x0: videoCurrentTime,
      y0: 0,
      x1: videoCurrentTime,
      y1: 1,
      xref: "x",
      yref: "paper",
      line: { color: "grey", width: 1 },
      layer: "below"
    },
    {
      type: "rect",
      x0: startTime,
      y0: Math.min(...currentData.linePlot.data),
      x1: blurEnd,
      y1: Math.max(...currentData.linePlot.data),
      fillcolor: "rgba(128, 128, 128, 0.4)",
      line: { width: 0 },
      layer: "above"
    },
    {
      type: "rect",
      x0: blurStart,
      y0: Math.min(...currentData.linePlot.data),
      x1: endTime,
      y1: Math.max(...currentData.linePlot.data),
      fillcolor: "rgba(128, 128, 128, 0.4)",
      line: { width: 0 },
      layer: "above"
    }
  ];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      className: "relative flex flex-col items-center pr-8 pl-8 pb-8",
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "w-full max-w-5xl mb-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              className: "w-full rounded-lg border border-zinc-600 bg-zinc-700 px-4 py-2 text-left text-sm font-semibold text-gray-100 hover:bg-zinc-600",
              onClick: () => setShowAnalysisRange((open) => !open),
              children: [
                showAnalysisRange ? "▾" : "▸",
                " Analysis range & normalization"
              ]
            }
          ),
          showAnalysisRange && /* @__PURE__ */ jsxRuntimeExports.jsx(
            AnalysisRangePanel,
            {
              videoRef,
              cacheStart: Number((currentData.analysis_cache || { start_time: startTime }).start_time),
              cacheEnd: Number((currentData.analysis_cache || { end_time: endTime }).end_time),
              start: startTime,
              end: endTime,
              normStrategy: tasks[selectedTaskIndex]?.norm_strategy,
              onApply: applyCachedAnalysisRange
            }
          ),
          reanalysing && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-2 text-sm text-blue-200", children: "Recalculating from cached landmarks…" }),
          rangeError && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-2 text-sm text-red-300", children: rangeError })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: "w-full max-w-5xl p-4 bg-[#333338] rounded-xl",
            style: { minHeight: "400px" },
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              Plot,
              {
                ref: plotRef,
                data: [
                  {
                    y: currentData.linePlot.data,
                    x: currentData.linePlot.time,
                    name: "Trace",
                    type: "scatter",
                    mode: "lines",
                    marker: { color: "#1f77b4" }
                  },
                  {
                    y: currentData.peaks.data,
                    x: currentData.peaks.time,
                    name: "Peak values",
                    type: "scatter",
                    mode: "markers",
                    marker: { size: 10, color: "#decd6dff" }
                  },
                  {
                    y: currentData.valleys_start.data,
                    x: currentData.valleys_start.time,
                    name: "Valley start",
                    type: "scatter",
                    mode: "markers",
                    marker: { size: 10, color: "#76B041" }
                  },
                  {
                    y: currentData.valleys_end.data,
                    x: currentData.valleys_end.time,
                    name: "Valley end",
                    type: "scatter",
                    mode: "markers",
                    marker: { size: 10, color: "red" }
                  },
                  {
                    y: selectedPoint.peak_data,
                    x: selectedPoint.peak_time,
                    name: "Selected Point",
                    type: "scatter",
                    mode: "markers",
                    marker: { size: 13, color: "#01FDF6" }
                  },
                  {
                    y: tempCycle.valleyStart ? [tempCycle.valleyStart.y] : [],
                    x: tempCycle.valleyStart ? [tempCycle.valleyStart.x] : [],
                    name: "Pending Valley Start",
                    type: "scatter",
                    mode: "markers",
                    marker: {
                      size: 12,
                      color: "green",
                      symbol: "diamond-open",
                      line: { width: 2, color: "green" }
                    }
                  },
                  {
                    y: tempCycle.peak ? [tempCycle.peak.y] : [],
                    x: tempCycle.peak ? [tempCycle.peak.x] : [],
                    name: "Pending Peak",
                    type: "scatter",
                    mode: "markers",
                    marker: {
                      size: 12,
                      color: "purple",
                      symbol: "diamond-open",
                      line: { width: 2, color: "purple" }
                    }
                  }
                ],
                onClick: handleClickOnPlot,
                config: {
                  modeBarButtonsToRemove: [
                    "select2d",
                    "lasso2d"
                  ],
                  responsive: true,
                  displaylogo: false,
                  scrollZoom: true,
                  toImageButtonOptions: {
                    filename: tasks[selectedTaskIndex].fileName ? tasks[selectedTaskIndex].fileName + "_waveplot" : "WavePlot"
                  }
                },
                layout: {
                  plot_bgcolor: light ? "#ffffff" : "#39393F",
                  paper_bgcolor: light ? "#ffffff" : "#333338",
                  shapes,
                  dragmode: "pan",
                  xaxis: {
                    title: {
                      text: "Time [s]",
                      standoff: 20,
                      font: { color: light ? "#18181b" : "#f6f3f3ff" }
                    },
                    gridcolor: light ? "#d4d4d8" : "#3F3F46",
                    tickfont: { color: light ? "#27272a" : "#f3f4f6" },
                    range: [startTime, endTime],
                    fixedrange: false
                  },
                  yaxis: {
                    title: {
                      text: "Distance",
                      standoff: 20,
                      font: { color: light ? "#18181b" : "#f3f4f6" }
                    },
                    gridcolor: light ? "#d4d4d8" : "#3F3F46",
                    tickfont: { color: light ? "#27272a" : "#f3f4f6" },
                    automargin: true,
                    fixedrange: false
                  },
                  height: 400,
                  margin: { t: 10, r: 10, b: 40, l: 50 },
                  legend: {
                    x: 1,
                    y: 1,
                    xanchor: "right",
                    yanchor: "top",
                    bgcolor: light ? "rgba(255,255,255,0.9)" : "rgba(51, 51, 56, 0.8)",
                    font: {
                      color: light ? "#18181b" : "#f3f4f6",
                      size: 12,
                      family: "Arial, sans-serif"
                    }
                  },
                  autosize: true,
                  uirevision: uiRevision
                },
                style: {
                  width: "100%",
                  height: "400px",
                  borderRadius: "1rem"
                },
                useResizeHandler: true
              }
            )
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative w-full max-w-5xl mt-4", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex justify-center gap-4", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              Button,
              {
                variant: "contained",
                onClick: () => {
                  setTaskFlags({ addNew: true, remove: false });
                  setAddPointName("valley_start");
                  showPopUp("Please select the new valley start point.");
                },
                sx: {
                  bgcolor: "primary.main",
                  "&:hover": { bgcolor: "primary.dark" },
                  textTransform: "none",
                  fontWeight: "bold",
                  px: 3,
                  py: 1
                },
                children: "Add Cycle"
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              Button,
              {
                variant: "contained",
                onClick: () => {
                  setTaskFlags({ addNew: false, remove: true });
                  showPopUp("Click on any point from the cycle you want to remove.");
                },
                sx: {
                  bgcolor: "primary.main",
                  "&:hover": { bgcolor: "primary.dark" },
                  textTransform: "none",
                  fontWeight: "bold",
                  px: 3,
                  py: 1
                },
                children: "Remove Cycle"
              }
            )
          ] }),
          popup.show && /* @__PURE__ */ jsxRuntimeExports.jsx(
            "div",
            {
              className: "absolute left-1/2 transform -translate-x-1/2 bg-white p-4 rounded-lg shadow-lg mt-2 w-3/4 max-w-xl z-50",
              style: { top: "100%" },
              children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex justify-between items-center", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-gray-800", children: popup.msg }),
                /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "button",
                  {
                    className: "font-bold ml-4 text-gray-600",
                    onClick: cancelCurrentTask,
                    "aria-label": "Close popup",
                    children: "X"
                  }
                )
              ] })
            }
          ),
          alertPopup.show && /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "div",
            {
              className: "absolute left-1/2 transform -translate-x-1/2 bg-white p-4 rounded-lg shadow-lg mt-2 w-3/4 max-w-xl z-50",
              style: { top: "100%" },
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex justify-between items-center", children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-gray-800", children: alertPopup.msg }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx(
                    "button",
                    {
                      className: "font-bold ml-4 text-gray-600",
                      onClick: cancelCurrentTask,
                      "aria-label": "Close alert",
                      children: "X"
                    }
                  )
                ] }),
                /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex justify-center gap-4 mt-4", children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx(
                    Button,
                    {
                      variant: "contained",
                      onClick: cancelCurrentTask,
                      sx: { textTransform: "none", fontWeight: "bold" },
                      children: "Cancel"
                    }
                  ),
                  /* @__PURE__ */ jsxRuntimeExports.jsx(
                    Button,
                    {
                      variant: "contained",
                      onClick: continueAlert,
                      sx: { textTransform: "none", fontWeight: "bold" },
                      children: "Continue"
                    }
                  )
                ] })
              ]
            }
          )
        ] })
      ]
    }
  );
};
export {
  ScatterPlot as S,
  WavePlotEditable as W
};
