import { j as jsxRuntimeExports } from "./index-D5uQjtsf.js";
import { W as WavePlotEditable, S as ScatterPlot } from "./WavePlotEditable-tt0QZAXJ.js";
import "./react-plotly-BE7kqALW.js";
const ToeTappingLeft = ({
  selectedTaskIndex,
  tasks,
  setTasks,
  fileName,
  videoRef,
  startTime,
  endTime,
  handleJSONUpload
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col overflow-auto", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "pt-2 border-b border-gray-300", children: tasks[selectedTaskIndex].data?.linePlot ? /* @__PURE__ */ jsxRuntimeExports.jsx(
      WavePlotEditable,
      {
        selectedTaskIndex,
        tasks,
        setTasks,
        videoRef,
        startTime,
        endTime,
        handleJSONUpload
      }
    ) : null }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "pt-6", children: tasks[selectedTaskIndex].data?.radarTable ? /* @__PURE__ */ jsxRuntimeExports.jsx(
      ScatterPlot,
      {
        selectedTaskIndex,
        tasks,
        fileName
      }
    ) : null })
  ] });
};
export {
  ToeTappingLeft as default
};
