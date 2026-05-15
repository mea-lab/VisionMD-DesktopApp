import React, { useState, useRef, useEffect, useSyncExternalStore } from 'react';
import IconButton from '@mui/material/IconButton';
import Collapse from '@mui/material/Collapse';
import HighlightOffIcon from '@mui/icons-material/HighlightOff';
import TouchApp from '@mui/icons-material/TouchApp';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import Tooltip from '@mui/material/Tooltip';

const HandTremorRightElbowExtended = ({
  task,
  taskTypeIndex,
  onFieldChange,
  onTaskDelete,
  onTimeMark,
  onTimeClick,
  options,
  taskGlobals,
  setTaskGlobals,
}) => {
  const [open, setOpen] = useState(true);
  const taskSelectionRef = useRef(null);

  const defaultIntrinsic = task.intrinsic_matrix || Array.from({ length: 3 }, () => Array(3).fill(null));
  const defaultExtrinsic = task.extrinsic_matrix || Array.from({ length: 4 }, () => Array(4).fill(null));

  const h = taskGlobals.height ?? null;
  const fov = taskGlobals.field_of_view ?? null;
  const sensorW = taskGlobals.sensor_width ?? null;
  const sensorH = taskGlobals.sensor_height ?? null;
  const fl = taskGlobals.focal_length ?? null;
  const intrinsicMatrix = taskGlobals.intrinsic_matrix || defaultIntrinsic;
  const extrinsicMatrix = taskGlobals.extrinsic_matrix || defaultExtrinsic;

  const [showCameraProperties, setShowCameraProperties] = useState(false);
  const [showIntrinsic, setShowIntrinsic] = useState(false);
  const [showExtrinsic, setShowExtrinsic] = useState(false);

  const handleTaskChange = (selectedTask) => {
    onFieldChange(selectedTask.value, 'name', task);
  };

  useEffect(() => {
    if (task.field_of_view !== undefined && taskGlobals.field_of_view === undefined) {
      setTaskGlobals({ field_of_view: task.field_of_view });
    }
    if (task.focal_length !== undefined && taskGlobals.focal_length === undefined) {
      setTaskGlobals({ focal_length: task.focal_length });
    }
    if (task.sensor_width !== undefined && taskGlobals.sensor_width === undefined) {
      setTaskGlobals({ sensor_width: task.sensor_width });
    }
    if (task.sensor_height !== undefined && taskGlobals.sensor_height === undefined) {
      setTaskGlobals({ sensor_height: task.sensor_height });
    }
    if (task.height !== undefined && taskGlobals.height === undefined) {
      setTaskGlobals({ height: task.height });
    }
    if (task.intrinsic_matrix !== undefined && taskGlobals.intrinsic_matrix === undefined) {
      setTaskGlobals({ intrinsic_matrix: task.intrinsic_matrix });
    }
    if (task.extrinsic_matrix !== undefined && taskGlobals.extrinsic_matrix === undefined) {
      setTaskGlobals({ extrinsic_matrix: task.extrinsic_matrix });
    }
  }, []);

  useEffect(() => {
    if (typeof taskGlobals.field_of_view !== 'undefined') {
      onFieldChange(taskGlobals.field_of_view, 'field_of_view', task);
    }
    if (typeof taskGlobals.focal_length !== 'undefined') {
      console.log("Setting local focal_length for task #", taskGlobals.focal_length)
      onFieldChange(taskGlobals.focal_length, 'focal_length', task);
    }
    if (typeof taskGlobals.sensor_width !== 'undefined') {
      onFieldChange(taskGlobals.sensor_width, 'sensor_width', task);
    }
    if (typeof taskGlobals.sensor_height !== 'undefined') {
      onFieldChange(taskGlobals.sensor_height, 'sensor_height', task);
    }
    if (typeof taskGlobals.height !== 'undefined') {
      onFieldChange(taskGlobals.height, 'height', task);
    }
    if (typeof taskGlobals.intrinsic_matrix !== 'undefined') {
      onFieldChange(taskGlobals.intrinsic_matrix, 'intrinsic_matrix', task);
    }
    if (typeof taskGlobals.extrinsic_matrix !== 'undefined') {
      onFieldChange(taskGlobals.extrinsic_matrix, 'extrinsic_matrix', task);
    }
  }, [taskGlobals]);

  // Renders a size×size matrix editor
  const renderCameraPropertiesEditor = (
    fov,
    sensorHeight,
    sensorWidth,
    focalLength,
    intrinsicMatrix,
    extrinsicMatrix,
    showIntrinsic,
    showExtrinsic,
  ) => {
    return (
      <div>
        {/* Field of View */}
        <div className="py-1.5 flex justify-between items-center">
          <label className="text-gray-100">Field of View (°):</label>
          <div>
            <input
              type="number"
              step="any"
              className="border border-zinc-500 rounded-lg bg-transparent p-1 pl-2 py-1.5 w-20 text-left text-gray-100 [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [&input[type=number]]:appearance-none"
              value={fov || ''}
              placeholder='55'
              onChange={e => {
                const v = e.target.value === '' ? null : +e.target.value;
                setTaskGlobals({ field_of_view: v });
                onFieldChange(v, 'field_of_view', task);
              }}
            />
            <Tooltip
              arrow
              title="Enter the field of view (degrees) along the longer side of the video frame. (Optional)"
            >
              <HelpOutlineIcon className="ml-1 text-gray-100 cursor-pointer" fontSize="small" />
            </Tooltip>
          </div>
        </div>

      {/* Sensor Width (mm) */}
      <div className="py-1.5 flex justify-between items-center">
        <label className="text-gray-100">Sensor Pixel Width (µm/pixels):</label>
        <div>
          <input
            type="number"
            step="any"
            className="border border-zinc-500 rounded-lg bg-transparent p-1 pl-2 py-1.5 w-20 text-left text-gray-100 [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [&input[type=number]]:appearance-none"
            value={sensorWidth || ''}
            onChange={e => {
              const v = e.target.value === '' ? null : +e.target.value;
              setTaskGlobals({ sensor_width: v });
              onFieldChange(v, 'sensor_width', task);
            }}
          />
          <Tooltip
            arrow
            title="Enter the sensor pixel width (µm/pixels) of the video camera. (Optional)"
          >
            <HelpOutlineIcon className="ml-1 text-gray-100 cursor-pointer" fontSize="small" />
          </Tooltip>
        </div>
      </div>

      {/* Sensor Height (mm) */}
      <div className="py-1.5 flex justify-between items-center">
        <label className="text-gray-100">Sensor Pixel Height (µm/pixels):</label>
        <div>
          <input
            type="number"
            step="any"
            className="border border-zinc-500 rounded-lg bg-transparent p-1 pl-2 py-1.5 w-20 text-left text-gray-100 [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [&input[type=number]]:appearance-none"
            value={sensorHeight || ''}
            onChange={e => {
              const v = e.target.value === '' ? null : +e.target.value;
              setTaskGlobals({ sensor_height: v });
              onFieldChange(v, 'sensor_height', task);
            }}
          />
          <Tooltip
            arrow
            title="Enter the sensor pixel height (µm/pixels) of the video camera. (Optional)"
          >
            <HelpOutlineIcon className="ml-1 text-gray-100 cursor-pointer" fontSize="small" />
          </Tooltip>
        </div>
      </div>

      {/* Focal Length (mm) */}
      <div className="py-1.5 flex justify-between items-center">
        <label className="text-gray-100">Focal Length (mm):</label>
        <div>
          <input
            type="number"
            step="any"
            className="border border-zinc-500 rounded-lg bg-transparent p-1 pl-2 py-1.5 w-20 text-left text-gray-100 [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [&input[type=number]]:appearance-none"
            value={fl || ''}
            onChange={e => {
              const v = e.target.value === '' ? null : +e.target.value;
              setTaskGlobals({ focal_length: v });
              onFieldChange(v, 'focal_length', task);
            }}
          />
          <Tooltip
            arrow
            title="Enter the true focal length (mm) of the video camera. (Optional)"
          >
            <HelpOutlineIcon className="ml-1 text-gray-100 cursor-pointer" fontSize="small" />
          </Tooltip>
        </div>
      </div>

        {/* Intrinsic Matrix Section */}
        <div className="py-1.5">
          <div
            className="flex items-center justify-between cursor-pointer select-none"
            onClick={() => setShowIntrinsic(p => !p)}
          >
            <span className="text-gray-100">Intrinsic Matrix:</span>
            <div>
              <ExpandMoreIcon className={`transition-transform duration-200 ${showIntrinsic ? 'rotate-180' : ''} text-gray-100`}/>
              <Tooltip
                arrow
                title="Enter the intrinsic matrix of the video camera. (Optional)"
              >
                <HelpOutlineIcon className="ml-1 text-gray-100 cursor-pointer" fontSize="small" />
              </Tooltip>
            </div>
          </div>
          <div className='flex justify-center'>
            <Collapse in={showIntrinsic} timeout="auto" unmountOnExit>
              <div className="mt-2 flex place-items-center grid gap-2 inline-grid" style={{ gridTemplateColumns: `repeat(3, auto)` }}>
                {intrinsicMatrix.map((row, i) =>
                  row.map((val, j) => (
                    <input
                      key={`int-${i}-${j}`}
                      type="number"
                      step="any"
                      className="border border-zinc-500 bg-transparent rounded-lg p-1 w-16 text-gray-100 text-center [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [&input[type=number]]:appearance-none"
                      value={val}
                      onChange={(e) => {
                        const newVal = e.target.value === '' ? null : +e.target.value;
                        const newMatrix = intrinsicMatrix.map((r) => [...r]);
                        newMatrix[i][j] = newVal;
                        setTaskGlobals({ intrinsic_matrix: newMatrix });
                        onFieldChange(newMatrix, 'intrinsic_matrix', task);
                      }}
                    />
                  ))
                )}
              </div>
            </Collapse>
          </div>
        </div>

        {/* Extrinsic Matrix Section */}
        <div className="py-1.5">
          <div
            className="flex items-center justify-between cursor-pointer select-none"
            onClick={() => setShowExtrinsic(p => !p)}
          >
            <span className="text-gray-100">Extrinsic Matrix:</span>
            <div>
              <ExpandMoreIcon className={`transition-transform duration-200 ${showExtrinsic ? 'rotate-180' : ''} text-gray-100`}/>
              <Tooltip
                arrow
                title="Enter the extrinsic matrix of the video camera. (Optional)"
              >
                <HelpOutlineIcon className="ml-1 text-gray-100 cursor-pointer" fontSize="small" />
              </Tooltip>
            </div>
          </div>
          <div className='flex justify-center'>
            <Collapse in={showExtrinsic} timeout="auto" unmountOnExit>
              <div className="mt-2 grid gap-2 place-items-center inline-grid" style={{ gridTemplateColumns: `repeat(4, minmax(0, 1fr))` }}>
                {extrinsicMatrix.map((row, i) =>
                  row.map((val, j) => (
                    <input
                      key={`ext-${i}-${j}`}
                      type="number"
                      step="any"
                      className="border border-zinc-500 bg-transparent rounded-lg p-1 w-16 text-gray-100 text-center [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [&input[type=number]]:appearance-none"
                      value={val}
                      onChange={(e) => {
                        const newVal = e.target.value === '' ? null : +e.target.value;
                        const newMatrix = extrinsicMatrix.map((r) => [...r]);
                        newMatrix[i][j] = newVal;
                        setTaskGlobals({ extrinsic_matrix: newMatrix });
                        onFieldChange(newMatrix, 'extrinsic_matrix', task);
                      }}
                    />
                  ))
                )}
              </div>
            </Collapse>
          </div>
        </div>

        {/* Buttons */}
        <div className="pb-2 pt-4 flex justify-between">
          <button
            className="px-3 py-1 bg-transparent border border-zinc-500 text-gray-100 rounded-lg w-20"
            onClick={() => setShowCameraProperties(false)}
          >
            Cancel
          </button>
          <button
            className="px-3 py-1 bg-[#1976d2] hover:bg-[#1565c0] text-gray-100 rounded-lg w-20"
            onClick={() => {
              onFieldChange(focalLength, 'focal_length', task);
              onFieldChange(intrinsicMatrix, 'intrinsic_matrix', task);
              onFieldChange(extrinsicMatrix, 'extrinsic_matrix', task);
              onFieldChange(sensorWidth, 'sensor_width', task);
              onFieldChange(sensorHeight, 'sensor_height', task);
              onFieldChange(fov, 'field_of_view', task);
              setShowCameraProperties(false);
            }}
          >
            Save
          </button>
        </div>
      </div>
    );
  };

  return (
    <div
      tabIndex={-1}
      className="flex-none border-2 border-zinc-500 rounded-lg mb-4 min-h-[50px] bg-zinc-600 
                 focus:border-blue-500 focus:outline-none
                 transition-all duration-500 ease-in-out"
      key={task.id}
      ref={taskSelectionRef}
    >
      {/* HEADER ROW */}
      <div className="flex items-center gap-4 justify-between px-4 py-2 bg-transparent text-gray-100">
        {task.name} #{task.id}
        <div>
          <IconButton
            size="small"
            className={`transform transition-transform duration-200 ${open ? 'rotate-180' : 'rotate-0'}`}
            onClick={e => { e.stopPropagation(); setOpen(o => !o); }}
            aria-label="Toggle details"
          >
            <ExpandMoreIcon className="text-gray-100" fontSize="small" />
          </IconButton>
          <IconButton
            size="small"
            aria-label="remove"
            onClick={() => onTaskDelete(task)}
          >
            <HighlightOffIcon className="text-gray-100" fontSize="inherit" />
          </IconButton>
        </div>
      </div>

      {/* DETAILS PANEL */}
      <Collapse in={open} timeout="auto" unmountOnExit className="border-t-2 border-zinc-500 w-full block">
        <div className="flex flex-row flex-wrap justify-between px-4 py-1 bg-transparent gap-y-3 py-2 rounded-b-lg">

          <div className="flex items-center space-x-2 justify-between min-w-[400px] w-full">
            {/* Task selector */}
            <div className="relative whitespace-nowrap">
              <label className="inline text-gray-100 whitespace-nowrap">Task: </label>
              <select
                className="p-1 pl-2 py-1.5 w-72 border border-zinc-500 text-left text-gray-100 rounded-lg bg-zinc-600"
                value={task.name}
                onChange={e => handleTaskChange({ value: e.target.value, label: e.target.value })}
              >
                <option value="" hidden>Select task</option>
                {options.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.value}
                  </option>
                ))}
              </select>
            </div>

            {/* Start time */}
            <div className="flex items-center gap-x-1">
              <label className="inline text-gray-100 whitespace-nowrap">Start: </label>
              <input
                className="p-1 pl-2 py-1.5 flex w-20 text-left text-gray-100 border border-zinc-500 rounded-lg bg-transparent"
                type="number"
                onChange={e => onFieldChange(e.target.value, 'start', task)}
                onDoubleClick={() => onTimeClick(task.start)}
                min={0}
                step={0.001}
                value={task.start}
              />
              <IconButton
                size="small"
                onClick={e => { e.stopPropagation(); onTimeMark('start', task); }}
              >
                <TouchApp fontSize="small" className="text-gray-100"/>
              </IconButton>
            </div>

            {/* End time */}
            <div className="flex items-center gap-x-1">
              <label className="inline text-gray-100 whitespace-nowrap">End: </label>
              <input
                className="p-1 pl-2 py-1.5 w-20 text-left text-gray-100 border border-zinc-500 rounded-lg bg-transparent"
                type="number"
                onChange={e => onFieldChange(e.target.value, 'end', task)}
                onDoubleClick={() => onTimeClick(task.end)}
                min={0}
                step={0.001}
                value={task.end}
              />
              <IconButton
                size="small"
                onClick={e => { e.stopPropagation(); onTimeMark('end', task); }}
              >
                <TouchApp fontSize="small" className="text-gray-100"/>
              </IconButton>
            </div>
          </div>

          {/* Render for first instance only */}
          {taskTypeIndex === 0 && (
            <>
              {/* Camera Properties & Height */}
              <div className="flex items-center justify-between space-x-2 min-w-[400px] w-full">
                <div className="flex items-center space-x-2">
                  <label className="text-gray-100 inline">Camera properties:</label>
                  <button
                    className="px-2 py-1.5 w-14 border border-zinc-500 rounded-lg text-gray-100 hover:bg-zinc-600"
                    onClick={() => setShowCameraProperties(true)}
                  >
                    Edit
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </Collapse>

      {/* Camera Properties */}
      {showCameraProperties && (
        <div className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-[#333338] border border-zinc-600 p-4 rounded-lg shadow-lg relative w-80">
            <h2 className="text text-gray-100 border-b border-zinc-600 flex justify-between bg-[#333338] py-2 mb-2">
              Edit Camera Properties
            </h2>
            {renderCameraPropertiesEditor(fov, sensorH, sensorW, fl, intrinsicMatrix, extrinsicMatrix, showIntrinsic, showExtrinsic)}
          </div>
        </div>
      )}
    </div>
  );
};

export default HandTremorRightElbowExtended;