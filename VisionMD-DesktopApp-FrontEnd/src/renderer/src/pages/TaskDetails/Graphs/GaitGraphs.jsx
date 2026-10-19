import { useMemo, useEffect, useState } from 'react';
import VideoSignalPlot from './VideoSignalPlot';

const formatSignalName = name => name.split('_').map(word => word[0].toUpperCase()+word.slice(1)).join(' ');

export default function GaitGraphs({ selectedTaskIndex, tasks, videoRef }) {
  const task = tasks?.[selectedTaskIndex] ?? {};
  const signals = useMemo(() => task.data?.signals ?? {}, [task.data?.signals]);
  const names = useMemo(() => Object.keys(signals), [signals]);
  const [selectedName, setSelectedName] = useState(() => names[0] ?? '');
  useEffect(() => {
    if (!names.includes(selectedName)) setSelectedName(names[0] ?? '');
  }, [names, selectedName]);
  const time = useMemo(() => {
    const count = signals[selectedName]?.length ?? 0;
    const start = task.start ?? 0;
    const dt = count > 1 ? ((task.end ?? start)-start)/(count-1) : 0;
    return Array.from({ length: count },(_,i) => start+i*dt);
  }, [selectedName, signals, task.start, task.end]);
  if (!selectedName) return null;
  return <div className="mx-4 min-w-0 rounded-lg bg-[#333338] p-4">
    <select aria-label="Gait signal" value={selectedName} onChange={event => setSelectedName(event.target.value)} className="mb-4 bg-[#333338] text-gray-100">
      {names.map(name => <option key={name} value={name}>{formatSignalName(name)} over Time</option>)}
    </select>
    <VideoSignalPlot title={formatSignalName(selectedName)} time={time} series={[{ name: formatSignalName(selectedName), values: signals[selectedName] ?? [], color: '#1f77b4' }]} videoRef={videoRef} />
  </div>;
}
