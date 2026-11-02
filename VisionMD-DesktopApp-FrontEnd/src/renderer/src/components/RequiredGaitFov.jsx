import { useRef, useState } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import { isGait } from './ParticipantHeight';

export const validFov = value => value !== null && value !== '' && value !== undefined && Number.isFinite(Number(value)) && Number(value) > 0 && Number(value) < 180;

export function useRequiredGaitFov(tasks, setTasks) {
  const [open, setOpen] = useState(false);
  const [fov, setFov] = useState('');
  const resolver = useRef(null);
  const tasksRef = useRef(tasks);
  tasksRef.current = tasks;
  const ensureFov = task => {
    task = tasksRef.current.find(item => item.id === task?.id) || task;
    if (!isGait(task) || validFov(task.field_of_view)) return Promise.resolve(task?.field_of_view);
    setFov('');
    setOpen(true);
    return new Promise(resolve => { resolver.current = resolve; });
  };
  const finish = accepted => {
    const value = accepted ? Number(fov) : null;
    if (accepted) setTasks(previous => previous.map(task => isGait(task) ? { ...task, field_of_view: value } : task));
    setOpen(false);
    resolver.current?.(value);
    resolver.current = null;
  };
  const fovDialog = <Dialog open={open} onClose={() => finish(false)}>
    <DialogTitle>Enter camera field of view</DialogTitle>
    <DialogContent>
      <p className="mb-4">Enter the field of view in degrees along the longer side of the video frame.</p>
      <label>Field of view (°): <input autoFocus aria-label="Field of view in degrees" type="number" min="0" max="180" step="any" value={fov} onChange={e => setFov(e.target.value)} className="w-24 rounded border border-zinc-500 p-1" /></label>
      <p className="mt-2 text-sm">Enter a value greater than 0 and less than 180.</p>
    </DialogContent>
    <DialogActions><button className="p-2" onClick={() => finish(false)}>Back</button>
      <button className="rounded bg-blue-600 p-2 text-white disabled:opacity-50" disabled={!validFov(fov)} onClick={() => finish(true)}>Save and continue</button></DialogActions>
  </Dialog>;
  return { ensureFov, fovDialog };
}
