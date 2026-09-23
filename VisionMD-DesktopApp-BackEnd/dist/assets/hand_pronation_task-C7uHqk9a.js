import { r as reactExports, j as jsxRuntimeExports, I as IconButton, f as default_1, h as default_1$1, C as Collapse, i as default_1$2 } from "./index-CcIK0TQJ.js";
const HandPronationTask = ({ side, task, onFieldChange, onTaskDelete, onTimeMark, onTimeClick, options }) => {
  const [open, setOpen] = reactExports.useState(true);
  reactExports.useEffect(() => {
    if (!task.norm_strategy) onFieldChange("NONE", "norm_strategy", task);
    if (!task.ps_method) onFieldChange("auto", "ps_method", task);
  }, []);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { tabIndex: -1, className: "flex-none border-2 border-zinc-500 rounded-lg mb-4 min-h-[50px] bg-zinc-600 focus:border-blue-500 focus:outline-none transition-all duration-500 ease-in-out", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-4 justify-between px-4 py-2 bg-transparent text-gray-100", children: [
      "Pronation/Supination ",
      side,
      " #",
      task.id,
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(IconButton, { size: "small", className: `transform transition-transform duration-200 ${open ? "rotate-180" : "rotate-0"}`, onClick: (event) => {
          event.stopPropagation();
          setOpen((value) => !value);
        }, "aria-label": "Toggle details", children: /* @__PURE__ */ jsxRuntimeExports.jsx(default_1, { className: "text-gray-100", fontSize: "small" }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(IconButton, { size: "small", "aria-label": "remove", onClick: () => onTaskDelete(task), children: /* @__PURE__ */ jsxRuntimeExports.jsx(default_1$1, { className: "text-gray-100", fontSize: "inherit" }) })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Collapse, { in: open, timeout: "auto", unmountOnExit: true, className: "border-t-2 border-zinc-500 w-full block", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-row flex-wrap justify-between px-4 py-2 bg-transparent gap-y-3 rounded-b-lg", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center space-x-2 justify-between min-w-[400px] w-full", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative whitespace-nowrap", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "inline text-gray-100 whitespace-nowrap", children: "Task: " }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("select", { className: "p-1 pl-2 py-1.5 w-56 border border-zinc-500 text-left text-gray-100 rounded-lg bg-zinc-600", value: task.name, onChange: (event) => onFieldChange(event.target.value, "name", task), children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", hidden: true, children: "Select task" }),
            options.map((option) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: option.value, children: option.label }, option.value))
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(TimeInput, { label: "Start", value: task.start, onChange: (value) => onFieldChange(value, "start", task), onMark: () => onTimeMark("start", task), onJump: () => onTimeClick(task.start) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(TimeInput, { label: "End", value: task.end, onChange: (value) => onFieldChange(value, "end", task), onMark: () => onTimeMark("end", task), onJump: () => onTimeClick(task.end) })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex w-full items-center gap-2 text-sm text-gray-100", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { htmlFor: `ps-method-${task.id}`, children: "Analysis engine:" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "select",
          {
            id: `ps-method-${task.id}`,
            value: task.ps_method || "auto",
            onChange: (event) => onFieldChange(event.target.value, "ps_method", task),
            className: "rounded-lg border border-zinc-500 bg-zinc-600 px-2 py-1.5 text-gray-100",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "auto", children: "MediaPipe screening, then WiLoR if needed" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "wilor", children: "WiLoR only" })
            ]
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-gray-200 text-sm", children: "The P/S signal is palm orientation in degrees around the forearm axis; it is not hand-size normalized." }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-amber-300 text-xs", children: "MediaPipe 3-D results are provisional and must be visually verified. Failed screening automatically falls back to WiLoR." })
    ] }) })
  ] });
};
const TimeInput = ({ label, value, onChange, onMark, onJump }) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-x-1", children: [
  /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { className: "inline text-gray-100 whitespace-nowrap", children: [
    label,
    ": "
  ] }),
  /* @__PURE__ */ jsxRuntimeExports.jsx("input", { className: "p-1 pl-2 py-1.5 flex w-20 text-left text-gray-100 border border-zinc-500 rounded-lg bg-transparent", type: "number", min: 0, step: 1e-3, value, onChange: (event) => onChange(event.target.value), onDoubleClick: onJump }),
  /* @__PURE__ */ jsxRuntimeExports.jsx(IconButton, { size: "small", onClick: (event) => {
    event.stopPropagation();
    onMark();
  }, children: /* @__PURE__ */ jsxRuntimeExports.jsx(default_1$2, { fontSize: "small", className: "text-gray-100" }) })
] });
export {
  HandPronationTask as default
};
