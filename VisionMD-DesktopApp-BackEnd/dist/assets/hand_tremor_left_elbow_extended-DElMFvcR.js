import { j as jsxRuntimeExports } from "./index-CcIK0TQJ.js";
import "./react-plotly-5EjayYNa.js";
import { F as FeatureTable } from "./uPlot.min-BuVdl80p.js";
import { T as TremorGraphs } from "./TremorGraphs-Bd2aF5qd.js";
const HandTremorLeft = ({
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
  HandTremorLeft as default
};
