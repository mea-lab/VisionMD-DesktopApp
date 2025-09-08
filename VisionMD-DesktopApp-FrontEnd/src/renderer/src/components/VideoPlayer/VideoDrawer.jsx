// src/components/VideoPlayer/VideoDrawer.jsx
import React, { useEffect, useRef, useCallback } from 'react';

const VideoDrawer = ({
  videoRef,
  boundingBoxes,
  fps,
  persons,
  tasks,
  landMarks,
  selectedTask,
  style,
  screen = 'default',
  isPlaying,
}) => {
  const canvasRef = useRef(null);
  const currentFrame = useRef(-1);
  const lastDrawnFrame = useRef(-1);
  const landmark_colors = tasks[selectedTask]?.data?.landmark_colors

  const getFrameNumber = useCallback(
    (timestamp) => Math.round(timestamp * fps),
    [fps]
  );

  const clearCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx.globalCompositeOperation = 'destination-over';
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.globalCompositeOperation = 'source-over';
    }
  }, []);

  // Modified drawVideoFrame to clip to a rounded rectangle
  const drawVideoFrame = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (video && canvas) {
      const ctx = canvas.getContext('2d');
      ctx.globalCompositeOperation = 'source-over';
      const radius = 20; 
      
      // Save current context state
      ctx.save();
      
      // Create a rounded rectangle clipping path
      ctx.beginPath();
      ctx.moveTo(radius, 0);
      ctx.lineTo(canvas.width - radius, 0);
      ctx.arcTo(canvas.width, 0, canvas.width, radius, radius);
      ctx.lineTo(canvas.width, canvas.height - radius);
      ctx.arcTo(canvas.width, canvas.height, canvas.width - radius, canvas.height, radius);
      ctx.lineTo(radius, canvas.height);
      ctx.arcTo(0, canvas.height, 0, canvas.height - radius, radius);
      ctx.lineTo(0, radius);
      ctx.arcTo(0, 0, radius, 0, radius);
      ctx.closePath();
      
      // Apply the clipping region
      ctx.clip();
      
      // Draw the video frame within the clipped area
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      
      // Restore context to remove clipping
      ctx.restore();
    }
  }, [videoRef]);

  const drawBoundingBoxes = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const boxData = boundingBoxes.find(
      (box) => box.frameNumber === currentFrame.current
    );
  
    if (boxData && boxData.data) {
      boxData.data.forEach((box) => {
        const x = Math.round(box.x) + 0.5;
        const y = Math.round(box.y) + 0.5;
        const width = Math.round(box.width);
        const height = Math.round(box.height);
  
        ctx.beginPath();
        ctx.strokeStyle = persons.find((p) => p.id === box.id && p.isSubject)
          ? 'green'
          : 'red';
        ctx.lineWidth = 10;
        ctx.rect(x, y, width, height);
        ctx.stroke();
      });
    }
  }, [boundingBoxes, persons]);

  const drawLandMarks = useCallback(() => {
    if (!tasks.length || selectedTask == null) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const currentTask = tasks[selectedTask];
    // compute the frame‐index relative to the start of this task
    const startFrame = Math.floor(currentTask.start * fps);
    const frameIndex = currentFrame.current - startFrame;
    if (
      frameIndex < 0 ||
      !landMarks ||
      frameIndex >= landMarks.length
    ) return;

    const joints2D = landMarks[frameIndex];
    const colors3D = landmark_colors;

    // pre‐compute the crop offset
    const offsetX = currentTask.x;
    const offsetY = currentTask.y;
    joints2D.forEach((pt, j) => {
      if (!pt || pt.length < 2) return;
      const [lx, ly] = pt;
      let fill = 'red';
      if (
        Array.isArray(colors3D) &&
        colors3D[frameIndex] &&
        Array.isArray(colors3D[frameIndex][j])
      ) {
        const [r, g, b] = colors3D[frameIndex][j];
        fill = `rgb(${r}, ${g}, ${b})`;
      }
      ctx.fillStyle = fill;
      ctx.beginPath();
      ctx.arc(lx , ly , 12.5, 0, 2 * Math.PI);
      ctx.fill();
    });
  }, [tasks, selectedTask, fps, landMarks, landmark_colors]);


  // Modified drawFrame: we only draw bounding boxes when not in a taskBox time interval.
  const drawFrame = useCallback((currentTime) => {
      const video = videoRef.current;
      if (!video) return;
      const frameNumber = getFrameNumber(currentTime);
      lastDrawnFrame.current = frameNumber;
      currentFrame.current = frameNumber;

      // Clear canvas and draw the current video frame as background.
      clearCanvas();
      drawVideoFrame();

      // Check if currentTime is within any taskBox's time window.
      const inTaskTime = tasks.some((task) => currentTime >= task.start && currentTime <= task.end);
      if (screen === 'subject_resolution') {
        drawBoundingBoxes();
      }

      if (screen === 'tasks' && !inTaskTime) {
        drawBoundingBoxes();
      }

      if (screen === 'taskDetails' && isPlaying) {
        drawLandMarks();
      }
    },
    [getFrameNumber, clearCanvas, drawVideoFrame, drawBoundingBoxes, drawLandMarks, landmark_colors, tasks, screen, isPlaying]
  );

  // Set canvas dimensions and start the continuous render loop.
  useEffect(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
  
    const setCanvasDimensions = () => {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    };
  
    if (video.readyState >= 1) {
      setCanvasDimensions();
    } else {
      video.addEventListener('loadedmetadata', setCanvasDimensions);
    }
  
    let frameCallbackId;
    const render = (now, metadata) => {
      drawFrame(metadata.mediaTime);
      frameCallbackId = video.requestVideoFrameCallback(render);
    };
  
    frameCallbackId = video.requestVideoFrameCallback(render);  
    return () => {
      video.removeEventListener('loadedmetadata', setCanvasDimensions);
      if (video.cancelVideoFrameCallback) {
        video.cancelVideoFrameCallback(frameCallbackId);
      }
    };
  }, [videoRef, drawFrame]);

  useEffect(() => {
    lastDrawnFrame.current = -1;
    if (videoRef?.current) {
      drawFrame(videoRef.current.currentTime);
    }
  }, [persons, tasks, landMarks, landmark_colors, selectedTask, screen, drawFrame, videoRef, isPlaying]);
  
  return (
    <canvas
      ref={canvasRef}
      style={style}
    />
  );
};

export default VideoDrawer;
