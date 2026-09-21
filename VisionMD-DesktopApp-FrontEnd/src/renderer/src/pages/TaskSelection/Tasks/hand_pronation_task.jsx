import { useEffect, useState } from 'react';
import { Collapse, IconButton } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import HighlightOffIcon from '@mui/icons-material/HighlightOff';
import TouchApp from '@mui/icons-material/TouchApp';

/** Shared setup panel for left and right pronation/supination tasks. */
const HandPronationTask = ({ side, task, onFieldChange, onTaskDelete, onTimeMark, onTimeClick, options }) => {
  const [open, setOpen] = useState(true);

  useEffect(() => {
    // P/S is an angular signal, so hand-size normalization is intentionally
    // not applied.  The backend always keeps the scale at 1 degree/degree.
    if (!task.norm_strategy) onFieldChange('NONE', 'norm_strategy', task);
  }, []);

  return (
    <div tabIndex={-1} className="flex-none border-2 border-zinc-500 rounded-lg mb-4 min-h-[50px] bg-zinc-600 focus:border-blue-500 focus:outline-none transition-all duration-500 ease-in-out">
      <div className="flex items-center gap-4 justify-between px-4 py-2 bg-transparent text-gray-100">
        Hand Pronation/Supination {side} #{task.id}
        <div>
          <IconButton size="small" className={`transform transition-transform duration-200 ${open ? 'rotate-180' : 'rotate-0'}`} onClick={event => { event.stopPropagation(); setOpen(value => !value); }} aria-label="Toggle details">
            <ExpandMoreIcon className="text-gray-100" fontSize="small" />
          </IconButton>
          <IconButton size="small" aria-label="remove" onClick={() => onTaskDelete(task)}>
            <HighlightOffIcon className="text-gray-100" fontSize="inherit" />
          </IconButton>
        </div>
      </div>
      <Collapse in={open} timeout="auto" unmountOnExit className="border-t-2 border-zinc-500 w-full block">
        <div className="flex flex-row flex-wrap justify-between px-4 py-2 bg-transparent gap-y-3 rounded-b-lg">
          <div className="flex items-center space-x-2 justify-between min-w-[400px] w-full">
            <div className="relative whitespace-nowrap">
              <label className="inline text-gray-100 whitespace-nowrap">Task: </label>
              <select className="p-1 pl-2 py-1.5 w-56 border border-zinc-500 text-left text-gray-100 rounded-lg bg-zinc-600" value={task.name} onChange={event => onFieldChange(event.target.value, 'name', task)}>
                <option value="" hidden>Select task</option>
                {options.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </div>
            <TimeInput label="Start" value={task.start} onChange={value => onFieldChange(value, 'start', task)} onMark={() => onTimeMark('start', task)} onJump={() => onTimeClick(task.start)} />
            <TimeInput label="End" value={task.end} onChange={value => onFieldChange(value, 'end', task)} onMark={() => onTimeMark('end', task)} onJump={() => onTimeClick(task.end)} />
          </div>
          <p className="text-gray-200 text-sm">The P/S signal is palm orientation in degrees around the forearm axis; it is not hand-size normalized.</p>
        </div>
      </Collapse>
    </div>
  );
};

const TimeInput = ({ label, value, onChange, onMark, onJump }) => (
  <div className="flex items-center gap-x-1">
    <label className="inline text-gray-100 whitespace-nowrap">{label}: </label>
    <input className="p-1 pl-2 py-1.5 flex w-20 text-left text-gray-100 border border-zinc-500 rounded-lg bg-transparent" type="number" min={0} step={0.001} value={value} onChange={event => onChange(event.target.value)} onDoubleClick={onJump} />
    <IconButton size="small" onClick={event => { event.stopPropagation(); onMark(); }}><TouchApp fontSize="small" className="text-gray-100" /></IconButton>
  </div>
);

export default HandPronationTask;
