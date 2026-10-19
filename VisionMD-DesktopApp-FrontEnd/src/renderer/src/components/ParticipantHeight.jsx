import { useRef, useState } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';

export const validHeight = height => Number.isFinite(Number(height)) && Number(height) > 0;
export const isGait = task => task?.name?.toLowerCase() === 'gait';
export const requiresParticipantHeight = task => ['gait', 'sit to stand'].includes(task?.name?.toLowerCase());

export function HeightInput({ value, onChange }) {
  const [unit, setUnit] = useState('cm');
  const inches = validHeight(value) ? Number(value) / 2.54 : 0;
  const feet = Math.floor(Math.round(inches * 100) / 100 / 12);
  const remainder = Math.round((inches - feet * 12) * 100) / 100;
  const inputClass = 'w-20 rounded border border-zinc-500 bg-transparent p-1';
  return <div className="flex flex-wrap items-center gap-2">
    <span>Height:</span>
    <select aria-label="Height units" className="rounded border border-zinc-500 bg-transparent p-1" value={unit} onChange={e => setUnit(e.target.value)}>
      <option value="cm">cm</option><option value="ft">ft / in</option>
    </select>
    {unit === 'cm' ? <input aria-label="Height in centimeters" className={inputClass} type="number" min="0" step="any" value={value ?? ''} onChange={e => onChange(e.target.value === '' ? null : Number(e.target.value))} /> : <>
      <label><input aria-label="Height feet" className={inputClass} type="number" min="0" step="1" value={validHeight(value) ? feet : ''} onChange={e => onChange(e.target.value === '' ? null : (Number(e.target.value) * 12 + remainder) * 2.54)} /> ft</label>
      <label><input aria-label="Height inches" className={inputClass} type="number" min="0" max="11.99" step="0.01" value={validHeight(value) ? remainder : ''} onChange={e => { const n = Number(e.target.value); if (n >= 0 && n < 12) onChange((feet * 12 + n) * 2.54); }} /> in</label>
    </>}
  </div>;
}

export function useRequiredGaitHeight(tasks, setTasks) {
  const [open, setOpen] = useState(false);
  const [height, setHeight] = useState(null);
  const resolver = useRef(null);
  const tasksRef = useRef(tasks);
  tasksRef.current = tasks;
  const ensureHeight = task => {
    task = tasksRef.current.find(item => item.id === task?.id) || task;
    if (!requiresParticipantHeight(task) || validHeight(task.height)) return Promise.resolve(task?.height);
    setHeight(null);
    setOpen(true);
    return new Promise(resolve => { resolver.current = resolve; });
  };
  const finish = accepted => {
    const value = accepted ? Number(height) : null;
    if (accepted) setTasks(previous => previous.map(task => requiresParticipantHeight(task) ? { ...task, height: value } : task));
    setOpen(false);
    resolver.current?.(value);
    resolver.current = null;
  };
  const heightDialog = <Dialog open={open} onClose={() => finish(false)}>
    <DialogTitle>Enter participant height</DialogTitle>
    <DialogContent>
      <p className="mb-4">Participant height is required for gait and sit-to-stand setup.</p>
      <HeightInput value={height} onChange={setHeight} />
    </DialogContent>
    <DialogActions>
      <button className="p-2" onClick={() => finish(false)}>Back</button>
      <button className="rounded bg-blue-600 p-2 text-white disabled:opacity-50" disabled={!validHeight(height)} onClick={() => finish(true)}>Save and continue</button>
    </DialogActions>
  </Dialog>;
  return { ensureHeight, heightDialog };
}
