import React, { useEffect, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';
import HoverPlugin from 'wavesurfer.js/plugins/hover';
import Slider from '@mui/material/Slider';


const SubjectsWaveForm = ({ videoRef, isVideoReady }) => {
  const waveformRef = useRef(null);
  const waveSurfer = useRef(null);
  const [loadPercent, setLoadPercent] = useState(0);
  const [waveLoading, setWaveLoading] = useState(false);
  
  const onZoomChange = (zoomLevel) => {
    if (isVideoReady && waveSurfer.current && !waveLoading) {
      const duration = videoRef.current?.duration || 1;
      const pxPerSec = (670 / duration) * zoomLevel;
      waveSurfer.current.zoom(pxPerSec);
    }
  };

  const getWaveSurferOptions = () => {
    const duration = videoRef.current.duration;
    return {
      container: waveformRef.current,
      waveColor: '#1976d2',
      progressColor: '#0b397eff',
      cursorColor: 'gray',
      barWidth: 2,
      barRadius: 3,
      responsive: true,
      height: 100,
      backend: 'MediaElement',
      media: videoRef.current,
      mediaType: 'video',
      normalize: true,
      zoom: true,
      scrollParent: true,
      minPxPerSec: 680 / duration,
    };
  };

  // Initial zoom setup after waveSurfer is ready
  const setInitialZoom = () => {
    const duration = videoRef.current?.duration || 1;
    const pxPerSec = (670 / duration) * 1;
    waveSurfer.current.zoom(pxPerSec);
  };

  useEffect(() => {
    if (!isVideoReady || !videoRef?.current) return;

    if (waveSurfer.current) {
      waveSurfer.current.destroy();
    }

    waveSurfer.current = WaveSurfer.create(getWaveSurferOptions());
    waveSurfer.current.registerPlugin(
      HoverPlugin.create({
        labelColor: '#f3f4f6',
      })
    );

    waveSurfer.current.on('loading', percent => {
      setLoadPercent(percent);
      setWaveLoading(true);
    });

    waveSurfer.current.on('ready', () => {
      setWaveLoading(false);
      setInitialZoom();  // Ensure initial zoom level after waveform is ready
    });

    return () => {
      waveSurfer.current?.destroy();
    };
  }, [isVideoReady, videoRef]);

  return (
    <div className="flex flex-col justify-center items-center w-full pt-4 p-2">
      {isVideoReady && (
      <div className="flex flex-col w-full p-4 rounded-lg bg-[#333338]">
        <div className="w-full flex items-center justify-between pb-2 border-b-2 border-zinc-500">
          <div className="text-gray-100 text-left">
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
            onChange={(e) => onZoomChange(e.target.value)}
            aria-label="Zoom"
            valueLabelDisplay="auto"
            valueLabelFormat={value => `${value}x`}
          />
        </div>
        <div
          id="waveform"
          className="w-full py-2 overflow-x-auto bg-zinc-700" 
          ref={waveformRef}
        />
      </div>
      )}

      {!isVideoReady && (
      <div
        id="waveform"
        className="w-full px-8 py-2 bg-zinc-700 overflow-x-auto"
        ref={waveformRef}
      />
      )}
    </div>
  );
};

export default SubjectsWaveForm;
