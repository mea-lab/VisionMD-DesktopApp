// src/pages/TaskSelection/TasksWaveForm.jsx
import React, { useEffect, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';
import RegionsPlugin from 'wavesurfer.js/plugins/regions';
import Slider from '@mui/material/Slider';

const TasksWaveForm = ({
  videoRef,
  tasks,
  onTaskCreate,
  onTaskChange,
  isVideoReady,
}) => {
  const waveformRef = useRef(null);
  const waveSurferRef = useRef(null);
  const regionsPluginRef = useRef(null);
  const ignoreRef = useRef(false);
  const tasksRef = useRef(tasks);

  const [waveSurferReady, setWaveSurferReady] = useState(false);
  const [loadPercent, setLoadPercent] = useState(0)
  const [waveLoading, setWaveLoading] = useState(false);
  useEffect(() => {
    tasksRef.current = tasks;
  }, [tasks]);

  const getHighestId = () => tasksRef.current.reduce((max, t) => Math.max(max, t.id), 0);

  useEffect(() => {
    if (!isVideoReady || !videoRef.current) return;

    if (waveSurferRef.current) {
      waveSurferRef.current.destroy();
      waveSurferRef.current = null;
    }

    const ws = WaveSurfer.create({
      container: waveformRef.current,
      waveColor: '#1976d2',
      progressColor: '#0b397eff',
      cursorColor: 'gray',
      barWidth: 2,
      barRadius: 3,
      responsive: true,
      height: 100,
      minPxPerSec: 100,
      autoScroll: true,
      normalize: true,
      media: videoRef.current,
    });

    waveSurferRef.current = ws;
    regionsPluginRef.current = ws.registerPlugin(RegionsPlugin.create());
    regionsPluginRef.current.enableDragSelection({});

    ws.on('loading', percent => {
      setLoadPercent(percent);
      setWaveLoading(true);
    });

    ws.on('ready', () => {
      const duration = videoRef.current.duration || 1;
      ws.zoom(670 / duration);
      setWaveSurferReady(true);
      setWaveLoading(false);
    });


    regionsPluginRef.current.on('region-created', region => {
      if (ignoreRef.current || region.content) return;
      const start = Number(region.start.toFixed(3));
      const end = Number(region.end.toFixed(3));

      // DO NOT REMOVE: HACK NEEDED TO REMOVE GHOST REGIONS
      region.setOptions({
        color: 'rgba(0,0,0,0)',
        start: NaN,
        end: NaN
      });
      ignoreRef.current = true;
      region.remove()
      ignoreRef.current = false;

      const newTask = {
        id: getHighestId() + 1,
        start,
        end,
        name: 'Region',
        data: null,
      };

      onTaskCreate(newTask);
      if (videoRef.current) videoRef.current.currentTime = start + 0.05;
    });


    regionsPluginRef.current.on('region-updated', region => {
      if (ignoreRef.current) return;

      const original = tasksRef.current.find(t => t.id === region.id);
      if (!original) return;

      const start = Number(region.start.toFixed(3));
      const end = Number(region.end.toFixed(3));
      
      ignoreRef.current = true;
      region.remove();
      ignoreRef.current = false;

      const updatedTask = {
        ...original,
        start,
        end,
        data: null,
      };

      
      onTaskChange(updatedTask);
      if (videoRef.current) {
        videoRef.current.currentTime =
          Math.abs(original.start - start) > 0.001 ? start + 0.05 : end - 0.05;
      }
    });

    return () => {
      ws.destroy();
      waveSurferRef.current = null;
      regionsPluginRef.current = null;
      setWaveSurferReady(false);
    };
  }, [isVideoReady, videoRef]);

  useEffect(() => {
    if (!waveSurferReady || !regionsPluginRef.current) return;

    ignoreRef.current = true;
    regionsPluginRef.current.clearRegions();

    tasks.forEach(task => {
      regionsPluginRef.current.addRegion({
        id: task.id,
        content: (() => {
          const label = document.createElement('div');
          label.textContent = `${task.name} #${task.id}`;
          label.style.color = '#f3f4f6';
          label.style.padding = '4px 8px';
          return label;
        })(),
        start: task.start,
        end: task.end,
        drag: true,
        resize: true,
        color: 'rgba(0, 0, 0, 0.2)'
      });
    });

    ignoreRef.current = false;
  }, [tasks, waveSurferReady]);

  const handleZoom = (_, zoom) => {
    if (!waveSurferReady) return;
    const duration = videoRef.current?.duration || 1;
    waveSurferRef.current.zoom((670 / duration) * zoom);
  };

  return (
    <div className="flex flex-col justify-center items-center w-full pt-6 p-2">
      <div className="flex flex-col w-full p-4 rounded-lg bg-[#333338]">
        <div className="w-full flex items-center justify-between pb-2 border-b-2 border-zinc-500">
          <div className="text-left text-gray-100">
            {waveLoading
                ? `Loading Waveform: ${Math.round(loadPercent)}%...`
                : 'Waveform'}
          </div>
          <Slider
            orientation="horizontal"
            min={1}
            max={10}
            step={0.1}
            style={{ width: 200 }}
            onChange={handleZoom}
            aria-label="Zoom"
            valueLabelDisplay="auto"
            valueLabelFormat={v => `${v}x`}
          />
        </div>
        <div
          id="waveform"
          className="w-full py-2 bg-zinc-700 overflow-x-auto"
          ref={waveformRef}
        />
      </div>
    </div>
  );
};

export default TasksWaveForm;
