import { j as jsxRuntimeExports } from "./index-YG0Ujhki.js";
import "./react-plotly-HJSFZU32.js";
import { F as FeatureTable } from "./uPlot.min-sCbeWyp5.js";
import { T as TremorGraphs } from "./TremorGraphs-0OgOPOv9.js";
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
