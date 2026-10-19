import { useMemo, useEffect, useState } from 'react';
import VideoSignalPlot from './VideoSignalPlot';

const formatSignalName = name => name.split('_').map(word => word[0].toUpperCase()+word.slice(1)).join(' ');

/** Gait's graph card and selector, also configured for sit-to-stand signals. */
export default function GaitGraphs({ selectedTaskIndex, tasks, videoRef,
  plotGroups, initialSignal, markers, bands, controls, signalLabel = 'Gait signal', eventLegend }) {
  const task = tasks?.[selectedTaskIndex] ?? {};
  const signals = useMemo(() => task.data?.signals ?? {}, [task.data?.signals]);
  const groups = useMemo(() => {
    if (plotGroups) return plotGroups;
    return Object.keys(signals).map(name => {
      const values = signals[name];
      const start = task.start ?? 0;
      const dt = values.length > 1 ? ((task.end ?? start)-start)/(values.length-1) : 0;
      return { key:name,title:formatSignalName(name),time:Array.from({length:values.length},(_,i)=>start+i*dt),series:[{name:formatSignalName(name),values,color:'#1f77b4'}] };
    });
  }, [plotGroups, signals, task.start, task.end]);
  const [selectedName,setSelectedName] = useState(() => initialSignal || groups[0]?.key || '');
  useEffect(() => {
    if (!groups.some(group=>group.key===selectedName)) setSelectedName(initialSignal || groups[0]?.key || '');
  }, [groups, selectedName, initialSignal]);
  const selected = groups.find(group=>group.key===selectedName) || groups[0];
  if (!selected) return null;
  const { key: plotKey, ...plotProps } = selected;
  return <div className="mx-4 min-w-0 rounded-lg bg-[#333338] p-4">
    <select aria-label={signalLabel} value={selected.key} onChange={event=>setSelectedName(event.target.value)} className="mb-4 bg-[#333338] text-gray-100">
      {groups.map(group=><option key={group.key} value={group.key}>{group.title} over Time</option>)}
    </select>
    {controls && <div className="mb-3 flex flex-wrap gap-4 text-sm">{controls}</div>}
    {eventLegend && <div className="mb-3 flex flex-wrap gap-3 text-xs">{eventLegend}</div>}
    <VideoSignalPlot key={plotKey} {...plotProps} videoRef={videoRef} markers={markers} bands={bands} />
  </div>;
}
