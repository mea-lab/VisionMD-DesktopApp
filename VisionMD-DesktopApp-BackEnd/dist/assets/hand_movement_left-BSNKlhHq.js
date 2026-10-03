import { r as reactExports, j as jsxRuntimeExports, I as IconButton, f as default_1, h as default_1$1, C as Collapse, i as default_1$2 } from "./index-SsKyVGeV.js";
const HandMovementLeft = ({
  task,
  onFieldChange,
  onTaskDelete,
  onTimeMark,
  onTimeClick,
  options
}) => {
  const [open, setOpen] = reactExports.useState(true);
  const handleTaskChange = (selectedTask) => {
    onFieldChange(selectedTask.value, "name", task);
  };
  reactExports.useEffect(() => {
    if (!task.norm_strategy) {
      onFieldChange("PALMSIZE", "norm_strategy", task);
    }
  }, []);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      tabIndex: -1,
      className: "flex-none border-2 border-zinc-500 rounded-lg mb-4 min-h-[50px] bg-zinc-600 \n                 focus:border-blue-500 focus:outline-none\n                 transition-all duration-500 ease-in-out",
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: `flex items-center gap-4 justify-between px-4 py-2 bg-transparent text-gray-100`, children: [
          "Hand Movement Left #",
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
                  className: "p-1 pl-2 py-1.5 w-56 border border-zinc-500 text-left text-gray-100 rounded-lg bg-zinc-600",
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
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-between space-x-2 min-w-[400px] w-full", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center space-x-2", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "inline whitespace-nowrap text-gray-100", children: "Normalization: " }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "select",
              {
                className: "py-1.5 pl-2 w-[150px] border rounded-lg text-gray-100 bg-zinc-600 border-zinc-500",
                value: task?.norm_strategy ? task.norm_strategy : "PALMSIZE",
                onChange: (e) => onFieldChange(e.target.value, "norm_strategy", task),
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "INDEXSIZE", children: "Index finger size" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "THUMBSIZE", children: "Thumb size" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "PALMSIZE", children: "Palm size" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "MAXAMPLITUDE", children: "Max amplitude" })
                ]
              }
            )
          ] }) })
        ] }) })
      ]
    },
    task.id
  );
};
export {
  HandMovementLeft as default
};
