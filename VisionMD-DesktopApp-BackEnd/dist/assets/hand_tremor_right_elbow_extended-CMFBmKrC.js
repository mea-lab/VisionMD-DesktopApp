import { j as jsxRuntimeExports } from "./index--rBocHqq.js";
import "./react-plotly-BK6eLqDC.js";
import { F as FeatureTable } from "./uPlot.min-B-KwLxk-.js";
import { T as TremorGraphs } from "./TremorGraphs-CJDU-md0.js";
const HandTremorRight = ({
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
      TremorGraphs,
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
  HandTremorRight as default
};
