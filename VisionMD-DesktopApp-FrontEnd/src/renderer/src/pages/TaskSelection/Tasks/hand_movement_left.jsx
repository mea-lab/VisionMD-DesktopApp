import { useState, useRef, useEffect } from 'react';
import { IconButton, Collapse} from '@mui/material';
import HighlightOffIcon from '@mui/icons-material/HighlightOff';
import TouchApp from '@mui/icons-material/TouchApp';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';


const HandMovementLeft = ({
  task,
  onFieldChange,
  onTaskDelete,
  onTimeMark,
  onTimeClick,
  options,
}) => {
  const [open, setOpen] = useState(true);
  const renderCount = useRef(0);
  renderCount.current += 1;

  useEffect(() => {
    console.log(`Rendered ${renderCount.current} times`);
  });

  const handleTaskChange = selectedTask => {
    onFieldChange(selectedTask.value, 'name', task);
  };

  return (
    <div
      tabIndex={-1}
      className="flex-none border-2 border-zinc-500 rounded-lg mb-4 min-h-[50px] bg-zinc-600 
                 focus:border-blue-500 focus:outline-none
                 transition-all duration-500 ease-in-out"
      key={task.id}
    >
      {/*  HEADER ROW  */}
      <div className={`flex items-center gap-4 justify-between px-4 py-2 bg-transparent text-gray-100`}>
        Hand Movement Left #{task.id}
        <div>
          <IconButton
            size="small"
            className={`transform transition-transform duration-200 ${open ? 'rotate-180' : 'rotate-0'}`}
            onClick={e => { e.stopPropagation(); setOpen(o => !o); }}
            aria-label="Toggle details"
          >
            <ExpandMoreIcon className='text-gray-100' fontSize="small" />
          </IconButton>
          <IconButton
            size="small"
            aria-label="remove"
            onClick={() => onTaskDelete(task)}
          >
            <HighlightOffIcon className='text-gray-100' fontSize="inherit" />
          </IconButton>
        </div>
      </div>


      {/*  DETAILS PANEL  */}
      <Collapse in={open} timeout="auto" unmountOnExit className="border-t-2 border-zinc-500 w-full block">
        <div className="flex flex-row flex-wrap justify-between px-4 py-1 bg-transparent gap-y-3 py-2 rounded-b-lg">
          
          <div className="flex items-center space-x-2 justify-between min-w-[400px] w-full">
            {/* Task selector */}
            <div className="relative whitespace-nowrap">
              <label className="inline text-gray-100 whitespace-nowrap">Task: </label>
              <select
                className="p-1 pl-2 py-1.5 w-56 border border-zinc-500 text-left text-gray-100 rounded-lg bg-zinc-600"
                value={task.name}
                onChange={e => handleTaskChange({ value: e.target.value, label: e.target.value })}
              >
                <option value="" hidden>Select task</option>
                {options.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
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
          
          <div className="flex items-center justify-between space-x-2 min-w-[400px] w-full">
            {/* Normalization selector */}
            <div className="flex items-center space-x-2">
              <label className="inline whitespace-nowrap text-gray-100">Normalization: </label>
                <select
                  className="py-1.5 pl-2 w-[150px] border rounded-lg text-gray-100 bg-zinc-600 border-zinc-500"
                  value={task?.norm_strategy? task.norm_strategy: "INDEXSIZE"}
                  onChange={e => onFieldChange(e.target.value, 'norm_strategy', task)}
                >
                  <option value="INDEXSIZE">Index finger size</option>
                  <option value="THUMBSIZE">Thumb size</option>
                  <option value="PALMSIZE">Palm size</option>
                  <option value="MAXAMPLITUDE">Max amplitude</option>
                </select>
            </div>
          </div>
        </div>
      </Collapse>
    </div>
  );
};

export default HandMovementLeft;
