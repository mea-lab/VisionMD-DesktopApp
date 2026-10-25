// src/pages/TaskSelection/TasksWaveForm.jsx
import React, { useEffect, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';
import RegionsPlugin from 'wavesurfer.js/plugins/regions';
import Slider from '@mui/material/Slider';

const TasksWaveForm = ({
  videoRef,
  tasks,
  fps,
  onTaskCreate,
  onTaskChange,
  onTasksReplace,
  isVideoReady,
}) => {
  const waveformRef = useRef(null);
  const waveSurferRef = useRef(null);
  const regionsPluginRef = useRef(null);
  const previewMediaRef = useRef(null);
  const ignoreRef = useRef(false);
  const tasksRef = useRef(tasks);
  // This is deliberately page-local: leaving Task Selection discards the
  // temporary manual regions, while the chosen full-video task is persisted.
  const manualTasksBeforeFullVideoRef = useRef(null);

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

    // Keep waveform decoding isolated from the shared review video.  Binding
    // WaveSurfer to that element made video.duration grow during playback and
    // caused task/landmark frame indices to drift.
    const previewMedia = new Audio(videoRef.current.currentSrc || videoRef.current.src);
    previewMedia.muted = true;
    previewMediaRef.current = previewMedia;

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
      media: previewMedia,
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

    ws.on('interaction', time => {
      if (videoRef.current) videoRef.current.currentTime = time;
    });

    // Keep the independently decoded waveform visually synchronized with the
    // review video.  This preserves the moving playback bar without letting
    // WaveSurfer own or reload the shared <video> element.
    const syncWaveformToVideo = () => {
      const video = videoRef.current;
      if (!video || !Number.isFinite(video.currentTime)) return;
      ws.setTime(video.currentTime);
    };
    videoRef.current.addEventListener('timeupdate', syncWaveformToVideo);
    videoRef.current.addEventListener('seeked', syncWaveformToVideo);


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
      if (videoRef.current) videoRef.current.currentTime = start + 1 / fps;
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
        // Dragging a region is a manual range choice, not a full-video task.
        full_video: false,
        manual_range: { start, end },
        data: null,
      };

      
      onTaskChange(updatedTask);
      if (videoRef.current) {
        videoRef.current.currentTime =
          Math.abs(original.start - start) > 0.001 ? start + 1 / fps : end - 1 / fps;
      }
    });

    return () => {
      videoRef.current?.removeEventListener('timeupdate', syncWaveformToVideo);
      videoRef.current?.removeEventListener('seeked', syncWaveformToVideo);
      ws.destroy();
      previewMedia.pause();
      previewMedia.removeAttribute('src');
      previewMedia.load();
      previewMediaRef.current = null;
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

  const hasFullVideoTask =
    tasks.length === 1 && Boolean(tasks[0]?.full_video);

  const handleFullVideoChange = useFullVideo => {
    const duration = Number(videoRef.current?.duration);
    if (!Number.isFinite(duration) || duration <= 0) return;

    if (useFullVideo) {
      manualTasksBeforeFullVideoRef.current = tasks.map(task => ({ ...task }));
      const preservedId = tasks[0]?.id ?? 1;
      onTasksReplace([{
        id: preservedId,
        start: 0,
        end: Number(duration.toFixed(3)),
        name: 'Region',
        full_video: true,
        data: null,
      }]);
      return;
    }

    if (manualTasksBeforeFullVideoRef.current) {
      onTasksReplace(manualTasksBeforeFullVideoRef.current);
      manualTasksBeforeFullVideoRef.current = null;
    }
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
        <div className="flex justify-end pt-2 pr-1">
          <label
            className="inline-flex items-center gap-1.5 text-xs text-gray-100 cursor-pointer"
            title="Replace all regions with one task spanning the complete video"
          >
            <input
              type="checkbox"
              className="h-3.5 w-3.5 accent-blue-600"
              checked={hasFullVideoTask}
              disabled={!Number.isFinite(Number(videoRef.current?.duration))}
              onChange={event => handleFullVideoChange(event.target.checked)}
            />
            Full video
          </label>
        </div>
      </div>
    </div>
  );
};

export default TasksWaveForm;
