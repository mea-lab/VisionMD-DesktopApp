// src/components/commons/VideoPlayer/VideoPlayer.jsx
import React, { useEffect, useRef, useState, useCallback } from 'react';
import VideoControls from './VideoControls';
import Slider from '@mui/material/Slider';
import VideoDrawer from './VideoDrawer';
import InteractiveOverlays from './InteractiveOverlays';

const VideoPlayer = ({
  videoURL,
  videoRef,
  fps,
  boundingBoxes,
  persons,
  setVideoReady,
  fileName,
  screen,
  selectedTask,
  tasks,
  setTasks,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef(null);
  const [videoDimensions, setVideoDimensions] = useState({ width: 0, height: 0 });
  const [frameInput, setFrameInput] = useState(0);
  const [isEditing, setIsEditing] = useState(false);
  const [currentFrame, setCurrentFrame] = useState(0);

  const getFrameFromMediaTime = (time, fps) => Math.floor(time * fps + 1e-7)

  useEffect(() => {
    if (!isEditing) {
      setFrameInput(currentFrame);
    }
  }, [currentFrame, isEditing]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    let frameCallbackId;

    const updateFrameNumber = () => {
      const video = videoRef.current;
      if (!video) return;

      const frameIdx = getFrameFromMediaTime(video.currentTime, fps);
      setCurrentFrame(frameIdx);

      video.requestVideoFrameCallback(updateFrameNumber);
    };

    frameCallbackId = video.requestVideoFrameCallback(updateFrameNumber);
  }, [videoRef, fps]);

  // Update container size on mount and on window resize.
  const updateContainerSize = useCallback(() => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setContainerSize({ width: rect.width, height: rect.height });
    }
  }, []);

  useEffect(() => {
    updateContainerSize();
    window.addEventListener('resize', updateContainerSize);
    return () => window.removeEventListener('resize', updateContainerSize);
  }, [updateContainerSize]);

  // Clamp panOffset when container size or zoomLevel changes.
  useEffect(() => {
    if (containerSize.width && containerSize.height) {
      const maxOffsetX = ((zoomLevel - 1) * containerSize.width) / 2;
      const maxOffsetY = ((zoomLevel - 1) * containerSize.height) / 2;
      setPanOffset(prev => ({
        x: Math.max(-maxOffsetX, Math.min(prev.x, maxOffsetX)),
        y: Math.max(-maxOffsetY, Math.min(prev.y, maxOffsetY)),
      }));
    }
  }, [zoomLevel, containerSize]);

  // Keep playback clamped to the currently–selected task’s segment
  useEffect(() => {
    if (!videoRef.current || !tasks?.[selectedTask]) return;

    const vid = videoRef.current;
    const { start, end } = tasks[selectedTask];

    // Jump to the beginning of the segment once
    vid.currentTime = start + 1 / fps;
    setIsPlaying(!vid.paused);

    const handleUpdate = () => {
      if (vid.currentTime >= end - 0.05) {
        vid.pause();                      
        vid.currentTime = start;
        vid.play().catch(() => {});
      }
    };

    vid.addEventListener('timeupdate', handleUpdate);
    return () => vid.removeEventListener('timeupdate', handleUpdate);
  }, [selectedTask, videoRef]);

  const getTotalFrameCount = () => {
    if (videoRef.current && !isNaN(videoRef.current.duration)) {
      return Math.ceil(videoRef.current.duration * fps - 1e-6);
    }
    return 0;
  };

  // Pointer events for panning.
  const handlePointerDown = (e) => {
    if (zoomLevel > 1) {
      setIsDragging(true);
      dragStartRef.current = {
        x: e.clientX,
        y: e.clientY,
        panOffset: { ...panOffset },
      };
      e.target.setPointerCapture(e.pointerId);
    }
  };

  const handlePointerMove = (e) => {
    if (!isDragging || !dragStartRef.current) return;
    const dx = e.clientX - dragStartRef.current.x;
    const dy = e.clientY - dragStartRef.current.y;
    let newX = dragStartRef.current.panOffset.x + dx;
    let newY = dragStartRef.current.panOffset.y + dy;
    const maxOffsetX = ((zoomLevel - 1) * containerSize.width) / 2;
    const maxOffsetY = ((zoomLevel - 1) * containerSize.height) / 2;
    newX = Math.max(-maxOffsetX, Math.min(newX, maxOffsetX));
    newY = Math.max(-maxOffsetY, Math.min(newY, maxOffsetY));
    setPanOffset({ x: newX, y: newY });
  };

  const handlePointerUp = (e) => {
    setIsDragging(false);
    dragStartRef.current = null;
    e.target.releasePointerCapture(e.pointerId);
  };

  // New zoom handler that preserves the effective translation.
  const handleZoomChange = (e, value) => {
    const newZoom = value;
    // Compute the effective translation relative to the current zoom.
    const effectiveTranslation = {
      x: panOffset.x / zoomLevel,
      y: panOffset.y / zoomLevel,
    };
    // Calculate new pan offset so that the same effective translation is maintained.
    let newPan = {
      x: effectiveTranslation.x * newZoom,
      y: effectiveTranslation.y * newZoom,
    };

    // Clamp newPan to the allowed range based on the container size and new zoom.
    if (containerSize.width && containerSize.height) {
      const maxOffsetX = ((newZoom - 1) * containerSize.width) / 2;
      const maxOffsetY = ((newZoom - 1) * containerSize.height) / 2;
      newPan.x = Math.max(-maxOffsetX, Math.min(newPan.x, maxOffsetX));
      newPan.y = Math.max(-maxOffsetY, Math.min(newPan.y, maxOffsetY));
    }

    setZoomLevel(newZoom);
    setPanOffset(newPan);
  };
  

  return (
    <div className="flex flex-col justify-center items-center bg-zinc-800 w-full h-full">
      {videoURL && (
        
        <div className="h-full w-full flex justify-around flex-col">
          {/* Start Header Section */}
          {videoRef?.current?.readyState >= 1 && (
          <div className="w-full flex flex-row items-center justify-around py-4">
            {/* Title */}
            <div className="flex items-center justify-center">
              <span className="text-lg font-semibold text-gray-100">{fileName}</span>
            </div>
            {/* Frame Counter */}
            <div className="flex items-center space-x-1">
              <input
                className="w-24 text-center border border-zinc-700 bg-zinc-700 text-gray-100 rounded-lg px-2 py-1 focus:border-blue-500 focus:outline-none"
                type="text"
                value={frameInput}
                onChange={(e) => setFrameInput(e.target.value)}
                onFocus={() => setIsEditing(true)}
                onBlur={() => {
                  setIsEditing(false);
                  const newFrame = Number(frameInput);
                  if (!isNaN(newFrame) && videoRef.current) {
                    videoRef.current.currentTime = newFrame / fps;
                    setCurrentFrame(Math.floor(videoRef.current.currentTime * fps + 1e-7));
                  }
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') e.target.blur();
                }}
              />
              <span className="text-gray-100">/</span>
              <span className="text-gray-100">{getTotalFrameCount()}</span>
            </div>
          </div>
          )}
          {/* End Header Section */}

          <div className="flex flex-row justify-evenly overflow-hidden relative py-2">
          <div className="flex flex-col w-[10vw]"></div>
          <div
              ref={containerRef}
              className="relative overflow-hidden rounded-lg"
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              onPointerLeave={handlePointerUp}
              style={{touchAction: 'none' }}
            >
              <video
                src={videoURL}
                ref={videoRef}
                preload="auto"
                style={{
                  objectFit: 'contain',
                  width: '100%',
                  height: '100%',
                  opacity: 0, //VIDEO ELEMENT NEEDS TO BE HIDDEN AS IT BUFFERS, VIDEO DRAWER WILL DRAW THE VIDEO FRAMES
                }}
                onLoadedMetadata={() => {
                  setVideoReady(true);
                  updateContainerSize();
                  setVideoDimensions({
                    width: videoRef.current.videoWidth,
                    height: videoRef.current.videoHeight,
                  });
                }}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
              />
              <VideoDrawer
                videoRef={videoRef}
                boundingBoxes={boundingBoxes}
                fps={fps}
                persons={persons}
                tasks={tasks}
                landMarks={tasks[selectedTask]?.data?.landMarks}
                selectedTask={selectedTask}
                isPlaying={isPlaying}
                screen={screen}
                videoWidth={videoDimensions.width}
                videoHeight={videoDimensions.height}
                displayWidth={containerSize.width}
                displayHeight={containerSize.height}
                zoomLevel={zoomLevel}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
                  objectFit: 'contain',
                  transform: `scale(${zoomLevel}) translate(${panOffset.x / zoomLevel}px, ${panOffset.y / zoomLevel}px)`,
                  transformOrigin: 'center center',
                  background: 'transparent',
                }}
                
              />
              {boundingBoxes && (
                <InteractiveOverlays
                  tasks={tasks}
                  setTasks={setTasks}
                  fileName={fileName}
                  currentFrame={currentFrame}
                  zoomLevel={zoomLevel}
                  panOffset={panOffset}
                  screen={screen}
                  videoWidth={videoDimensions.width}
                  videoHeight={videoDimensions.height}
                  selectedTask={selectedTask}
                  fps={fps}
                  videoRef={videoRef}
                  isPlaying={isPlaying}
                  displayWidth={containerSize.width}
                  displayHeight={containerSize.height}
                />
              )}
            </div>

            <div className="flex flex-col items-center justify-center w-[10vw]">
              <Slider
                orientation="vertical"
                min={1}
                max={10}
                step={0.1}
                value={zoomLevel}
                onChange={handleZoomChange}
                aria-labelledby="Zoom"
                style={{ height: 300, width: 5}}
                valueLabelDisplay="auto"
                valueLabelFormat={(value) => `${value}x`}
              />
              <span className="text-md font-semibold text-gray-100 mt-4">Zoom</span>
            </div>
          </div>

          <div className="flex items-center pb-4 justify-center">
            <VideoControls videoRef={videoRef} fps={fps} isPlaying={isPlaying}/>
          </div>
        </div>
      )}
    </div>
  );
};

export default VideoPlayer;
