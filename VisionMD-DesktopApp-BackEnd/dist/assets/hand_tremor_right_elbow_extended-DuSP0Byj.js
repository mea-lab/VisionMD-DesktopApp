import { j as jsxRuntimeExports } from "./index-a3jZXBcQ.js";
import "./react-plotly-BcKaO30x.js";
import { F as FeatureTable } from "./uPlot.min-DiYs-YZ7.js";
import { T as TremorGraphs } from "./TremorGraphs-DFJ-p8or.js";
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
