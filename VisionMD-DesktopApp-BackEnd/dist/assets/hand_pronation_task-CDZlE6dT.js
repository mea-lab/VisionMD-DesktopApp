import { j as jsxRuntimeExports } from "./index-SsKyVGeV.js";
import { W as WavePlotEditable, S as ScatterPlot } from "./WavePlotEditable-doOKTxzj.js";
import "./react-plotly-Dri2kiCy.js";
const HandPronationTask = (props) => {
  const { selectedTaskIndex, tasks, setTasks, fileName, videoRef, startTime, endTime, handleJSONUpload } = props;
  const data = tasks[selectedTaskIndex]?.data;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col overflow-auto", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "pt-2 border-b border-gray-300", children: data?.linePlot && /* @__PURE__ */ jsxRuntimeExports.jsx(WavePlotEditable, { selectedTaskIndex, tasks, setTasks, videoRef, startTime, endTime, handleJSONUpload }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "pt-6", children: data?.radarTable && /* @__PURE__ */ jsxRuntimeExports.jsx(ScatterPlot, { selectedTaskIndex, tasks, fileName }) })
  ] });
};
export {
  HandPronationTask as default
};
