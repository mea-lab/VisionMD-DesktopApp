import { j as jsxRuntimeExports } from "./index-Bv0L31Av.js";
import "./react-plotly-CAMq4Hm1.js";
import { F as FeatureTable } from "./uPlot.min-CQbm4bST.js";
import { T as TremorGraphs } from "./TremorGraphs-DBrU5jw6.js";
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
