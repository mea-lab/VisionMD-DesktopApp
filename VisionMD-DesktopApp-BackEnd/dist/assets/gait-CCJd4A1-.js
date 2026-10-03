import { r as reactExports, j as jsxRuntimeExports, I as IconButton, f as default_1, h as default_1$1, C as Collapse, i as default_1$2, T as Tooltip } from "./index-piV9yOEw.js";
import { d as default_1$3 } from "./HelpOutline-DE-XAi4P.js";
const Gait = ({
  task,
  taskTypeIndex,
  onFieldChange,
  onTaskDelete,
  onTimeMark,
  onTimeClick,
  options,
  taskGlobals,
  setTaskGlobals
}) => {
  const [open, setOpen] = reactExports.useState(true);
  const taskSelectionRef = reactExports.useRef(null);
  const defaultIntrinsic = task.intrinsic_matrix || Array.from({ length: 3 }, () => Array(3).fill(null));
  const defaultExtrinsic = task.extrinsic_matrix || Array.from({ length: 4 }, () => Array(4).fill(null));
  const h = taskGlobals.height ?? null;
  const fov = taskGlobals.field_of_view ?? null;
  const sensorW = taskGlobals.sensor_width ?? null;
  const sensorH = taskGlobals.sensor_height ?? null;
  const fl = taskGlobals.focal_length ?? null;
  const intrinsicMatrix = taskGlobals.intrinsic_matrix || defaultIntrinsic;
  const extrinsicMatrix = taskGlobals.extrinsic_matrix || defaultExtrinsic;
  const [showCameraProperties, setShowCameraProperties] = reactExports.useState(false);
  const [showIntrinsic, setShowIntrinsic] = reactExports.useState(false);
  const [showExtrinsic, setShowExtrinsic] = reactExports.useState(false);
  const handleTaskChange = (selectedTask) => {
    onFieldChange(selectedTask.value, "name", task);
  };
  reactExports.useEffect(() => {
    if (task.field_of_view !== void 0 && taskGlobals.field_of_view === void 0) {
      setTaskGlobals({ field_of_view: task.field_of_view });
    }
    if (task.focal_length !== void 0 && taskGlobals.focal_length === void 0) {
      setTaskGlobals({ focal_length: task.focal_length });
    }
    if (task.sensor_width !== void 0 && taskGlobals.sensor_width === void 0) {
      setTaskGlobals({ sensor_width: task.sensor_width });
    }
    if (task.sensor_height !== void 0 && taskGlobals.sensor_height === void 0) {
      setTaskGlobals({ sensor_height: task.sensor_height });
    }
    if (task.height !== void 0 && taskGlobals.height === void 0) {
      setTaskGlobals({ height: task.height });
    }
    if (task.intrinsic_matrix !== void 0 && taskGlobals.intrinsic_matrix === void 0) {
      setTaskGlobals({ intrinsic_matrix: task.intrinsic_matrix });
    }
    if (task.extrinsic_matrix !== void 0 && taskGlobals.extrinsic_matrix === void 0) {
      setTaskGlobals({ extrinsic_matrix: task.extrinsic_matrix });
    }
  }, []);
  reactExports.useEffect(() => {
    if (typeof taskGlobals.field_of_view !== "undefined") {
      onFieldChange(taskGlobals.field_of_view, "field_of_view", task);
    }
    if (typeof taskGlobals.focal_length !== "undefined") {
      onFieldChange(taskGlobals.focal_length, "focal_length", task);
    }
    if (typeof taskGlobals.sensor_width !== "undefined") {
      onFieldChange(taskGlobals.sensor_width, "sensor_width", task);
    }
    if (typeof taskGlobals.sensor_height !== "undefined") {
      onFieldChange(taskGlobals.sensor_height, "sensor_height", task);
    }
    if (typeof taskGlobals.height !== "undefined") {
      onFieldChange(taskGlobals.height, "height", task);
    }
    if (typeof taskGlobals.intrinsic_matrix !== "undefined") {
      onFieldChange(taskGlobals.intrinsic_matrix, "intrinsic_matrix", task);
    }
    if (typeof taskGlobals.extrinsic_matrix !== "undefined") {
      onFieldChange(taskGlobals.extrinsic_matrix, "extrinsic_matrix", task);
    }
  }, [taskGlobals]);
  const renderCameraPropertiesEditor = (fov2, sensorHeight, sensorWidth, focalLength, intrinsicMatrix2, extrinsicMatrix2, showIntrinsic2, showExtrinsic2) => {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "py-1.5 flex justify-between items-center", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-gray-100", children: "Field of View (°):" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "number",
              step: "any",
              className: "border border-zinc-500 rounded-lg bg-transparent p-1 pl-2 py-1.5 w-20 text-left text-gray-100 [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [&input[type=number]]:appearance-none",
              value: fov2 || "",
              placeholder: "55",
              onChange: (e) => {
                const v = e.target.value === "" ? null : +e.target.value;
                setTaskGlobals({ field_of_view: v });
                onFieldChange(v, "field_of_view", task);
              }
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            Tooltip,
            {
              arrow: true,
              title: "Enter the field of view (degrees) along the longer side of the video frame. (Optional)",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(default_1$3, { className: "ml-1 text-gray-100 cursor-pointer", fontSize: "small" })
            }
          )
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "py-1.5 flex justify-between items-center", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-gray-100", children: "Sensor Pixel Width (µm/pixels):" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "number",
              step: "any",
              className: "border border-zinc-500 rounded-lg bg-transparent p-1 pl-2 py-1.5 w-20 text-left text-gray-100 [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [&input[type=number]]:appearance-none",
              value: sensorWidth || "",
              onChange: (e) => {
                const v = e.target.value === "" ? null : +e.target.value;
                setTaskGlobals({ sensor_width: v });
                onFieldChange(v, "sensor_width", task);
              }
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            Tooltip,
            {
              arrow: true,
              title: "Enter the sensor pixel width (µm/pixels) of the video camera. (Optional)",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(default_1$3, { className: "ml-1 text-gray-100 cursor-pointer", fontSize: "small" })
            }
          )
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "py-1.5 flex justify-between items-center", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-gray-100", children: "Sensor Pixel Height (µm/pixels):" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "number",
              step: "any",
              className: "border border-zinc-500 rounded-lg bg-transparent p-1 pl-2 py-1.5 w-20 text-left text-gray-100 [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [&input[type=number]]:appearance-none",
              value: sensorHeight || "",
              onChange: (e) => {
                const v = e.target.value === "" ? null : +e.target.value;
                setTaskGlobals({ sensor_height: v });
                onFieldChange(v, "sensor_height", task);
              }
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            Tooltip,
            {
              arrow: true,
              title: "Enter the sensor pixel height (µm/pixels) of the video camera. (Optional)",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(default_1$3, { className: "ml-1 text-gray-100 cursor-pointer", fontSize: "small" })
            }
          )
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "py-1.5 flex justify-between items-center", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-gray-100", children: "Focal Length (mm):" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "number",
              step: "any",
              className: "border border-zinc-500 rounded-lg bg-transparent p-1 pl-2 py-1.5 w-20 text-left text-gray-100 [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [&input[type=number]]:appearance-none",
              value: fl || "",
              onChange: (e) => {
                const v = e.target.value === "" ? null : +e.target.value;
                setTaskGlobals({ focal_length: v });
                onFieldChange(v, "focal_length", task);
              }
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            Tooltip,
            {
              arrow: true,
              title: "Enter the true focal length (mm) of the video camera. (Optional)",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(default_1$3, { className: "ml-1 text-gray-100 cursor-pointer", fontSize: "small" })
            }
          )
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "py-1.5", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "div",
          {
            className: "flex items-center justify-between cursor-pointer select-none",
            onClick: () => setShowIntrinsic((p) => !p),
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-gray-100", children: "Intrinsic Matrix:" }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(default_1, { className: `transition-transform duration-200 ${showIntrinsic2 ? "rotate-180" : ""} text-gray-100` }),
                /* @__PURE__ */ jsxRuntimeExports.jsx(
                  Tooltip,
                  {
                    arrow: true,
                    title: "Enter the intrinsic matrix of the video camera. (Optional)",
                    children: /* @__PURE__ */ jsxRuntimeExports.jsx(default_1$3, { className: "ml-1 text-gray-100 cursor-pointer", fontSize: "small" })
                  }
                )
              ] })
            ]
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex justify-center", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Collapse, { in: showIntrinsic2, timeout: "auto", unmountOnExit: true, children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-2 flex place-items-center grid gap-2 inline-grid", style: { gridTemplateColumns: `repeat(3, auto)` }, children: intrinsicMatrix2.map(
          (row, i) => row.map((val, j) => /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "number",
              step: "any",
              className: "border border-zinc-500 bg-transparent rounded-lg p-1 w-16 text-gray-100 text-center [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [&input[type=number]]:appearance-none",
              value: val,
              onChange: (e) => {
                const newVal = e.target.value === "" ? null : +e.target.value;
                const newMatrix = intrinsicMatrix2.map((r) => [...r]);
                newMatrix[i][j] = newVal;
                setTaskGlobals({ intrinsic_matrix: newMatrix });
                onFieldChange(newMatrix, "intrinsic_matrix", task);
              }
            },
            `int-${i}-${j}`
          ))
        ) }) }) })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "py-1.5", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "div",
          {
            className: "flex items-center justify-between cursor-pointer select-none",
            onClick: () => setShowExtrinsic((p) => !p),
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-gray-100", children: "Extrinsic Matrix:" }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(default_1, { className: `transition-transform duration-200 ${showExtrinsic2 ? "rotate-180" : ""} text-gray-100` }),
                /* @__PURE__ */ jsxRuntimeExports.jsx(
                  Tooltip,
                  {
                    arrow: true,
                    title: "Enter the extrinsic matrix of the video camera. (Optional)",
                    children: /* @__PURE__ */ jsxRuntimeExports.jsx(default_1$3, { className: "ml-1 text-gray-100 cursor-pointer", fontSize: "small" })
                  }
                )
              ] })
            ]
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex justify-center", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Collapse, { in: showExtrinsic2, timeout: "auto", unmountOnExit: true, children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-2 grid gap-2 place-items-center inline-grid", style: { gridTemplateColumns: `repeat(4, minmax(0, 1fr))` }, children: extrinsicMatrix2.map(
          (row, i) => row.map((val, j) => /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "number",
              step: "any",
              className: "border border-zinc-500 bg-transparent rounded-lg p-1 w-16 text-gray-100 text-center [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [&input[type=number]]:appearance-none",
              value: val,
              onChange: (e) => {
                const newVal = e.target.value === "" ? null : +e.target.value;
                const newMatrix = extrinsicMatrix2.map((r) => [...r]);
                newMatrix[i][j] = newVal;
                setTaskGlobals({ extrinsic_matrix: newMatrix });
                onFieldChange(newMatrix, "extrinsic_matrix", task);
              }
            },
            `ext-${i}-${j}`
          ))
        ) }) }) })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "pb-2 pt-4 flex justify-between", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            className: "px-3 py-1 bg-transparent border border-zinc-500 text-gray-100 rounded-lg w-20",
            onClick: () => setShowCameraProperties(false),
            children: "Cancel"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            className: "px-3 py-1 bg-[#1976d2] hover:bg-[#1565c0] text-gray-100 rounded-lg w-20",
            onClick: () => {
              onFieldChange(focalLength, "focal_length", task);
              onFieldChange(intrinsicMatrix2, "intrinsic_matrix", task);
              onFieldChange(extrinsicMatrix2, "extrinsic_matrix", task);
              onFieldChange(sensorWidth, "sensor_width", task);
              onFieldChange(sensorHeight, "sensor_height", task);
              onFieldChange(fov2, "field_of_view", task);
              setShowCameraProperties(false);
            },
            children: "Save"
          }
        )
      ] })
    ] });
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      tabIndex: -1,
      className: "flex-none border-2 border-zinc-500 rounded-lg mb-4 min-h-[50px] bg-zinc-600 \n                 focus:border-blue-500 focus:outline-none\n                 transition-all duration-500 ease-in-out",
      ref: taskSelectionRef,
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-4 justify-between px-4 py-2 bg-transparent text-gray-100", children: [
          task.name,
          " #",
          task.id,
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              IconButton,
              {
                size: "small",
                className: `transform transition-transform duration-200 ${open ? "rotate-180" : "rotate-0"}`,
                onClick: (e) => {
                  e.stopPropagation();
                  setOpen((o) => !o);
                },
                "aria-label": "Toggle details",
                children: /* @__PURE__ */ jsxRuntimeExports.jsx(default_1, { className: "text-gray-100", fontSize: "small" })
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              IconButton,
              {
                size: "small",
                "aria-label": "remove",
                onClick: () => onTaskDelete(task),
                children: /* @__PURE__ */ jsxRuntimeExports.jsx(default_1$1, { className: "text-gray-100", fontSize: "inherit" })
              }
            )
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(Collapse, { in: open, timeout: "auto", unmountOnExit: true, className: "border-t-2 border-zinc-500 w-full block", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-row flex-wrap justify-between px-4 py-1 bg-transparent gap-y-3 py-2 rounded-b-lg", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center space-x-2 justify-between min-w-[400px] w-full", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative whitespace-nowrap", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "inline text-gray-100 whitespace-nowrap", children: "Task: " }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs(
                "select",
                {
                  className: "p-1 pl-2 py-1.5 w-40 border border-zinc-500 text-left text-gray-100 rounded-lg bg-zinc-600",
                  value: task.name,
                  onChange: (e) => handleTaskChange({ value: e.target.value, label: e.target.value }),
                  children: [
                    /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", hidden: true, children: "Select task" }),
                    options.map((option) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: option.value, children: option.label }, option.value))
                  ]
                }
              )
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-x-1", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "inline text-gray-100 whitespace-nowrap", children: "Start: " }),
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "input",
                {
                  className: "p-1 pl-2 py-1.5 flex w-20 text-left text-gray-100 border border-zinc-500 rounded-lg bg-transparent",
                  type: "number",
                  onChange: (e) => onFieldChange(e.target.value, "start", task),
                  onDoubleClick: () => onTimeClick(task.start),
                  min: 0,
                  step: 1e-3,
                  value: task.start
                }
              ),
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                IconButton,
                {
                  size: "small",
                  onClick: (e) => {
                    e.stopPropagation();
                    onTimeMark("start", task);
                  },
                  children: /* @__PURE__ */ jsxRuntimeExports.jsx(default_1$2, { fontSize: "small", className: "text-gray-100" })
                }
              )
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-x-1", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "inline text-gray-100 whitespace-nowrap", children: "End: " }),
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "input",
                {
                  className: "p-1 pl-2 py-1.5 w-20 text-left text-gray-100 border border-zinc-500 rounded-lg bg-transparent",
                  type: "number",
                  onChange: (e) => onFieldChange(e.target.value, "end", task),
                  onDoubleClick: () => onTimeClick(task.end),
                  min: 0,
                  step: 1e-3,
                  value: task.end
                }
              ),
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                IconButton,
                {
                  size: "small",
                  onClick: (e) => {
                    e.stopPropagation();
                    onTimeMark("end", task);
                  },
                  children: /* @__PURE__ */ jsxRuntimeExports.jsx(default_1$2, { fontSize: "small", className: "text-gray-100" })
                }
              )
            ] })
          ] }),
          taskTypeIndex === 0 && /* @__PURE__ */ jsxRuntimeExports.jsx(jsxRuntimeExports.Fragment, { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between space-x-2 min-w-[400px] w-full", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center space-x-2", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-gray-100 inline", children: "Camera properties:" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  className: "px-2 py-1.5 w-14 border border-zinc-500 rounded-lg text-gray-100 hover:bg-zinc-500",
                  onClick: () => setShowCameraProperties(true),
                  children: "Edit"
                }
              )
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center space-x-1", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "inline text-gray-100 whitespace-nowrap", children: "Height (cm):" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "input",
                {
                  className: "p-1 pl-2 py-1.5 w-20 text-left text-gray-100 border border-zinc-500 rounded-lg bg-transparent",
                  type: "number",
                  inputMode: "decimal",
                  step: "any",
                  onChange: (e) => {
                    const v = e.target.value === "" ? null : parseFloat(e.target.value);
                    setTaskGlobals({ height: v });
                    onFieldChange(v, "height", task);
                  },
                  value: h ?? ""
                }
              )
            ] })
          ] }) })
        ] }) }),
        showCameraProperties && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-[#333338] border border-zinc-500 p-4 rounded-lg shadow-lg relative w-96", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text text-gray-100 border-b border-zinc-500 flex justify-between bg-[#333338] py-2 mb-2", children: "Edit Camera Properties" }),
          renderCameraPropertiesEditor(fov, sensorH, sensorW, fl, intrinsicMatrix, extrinsicMatrix, showIntrinsic, showExtrinsic)
        ] }) })
      ]
    },
    task.id
  );
};
export {
  Gait as default
};
