// src/components/VideoPlayer/VideoDrawer.jsx
import { useEffect, useRef, useCallback } from 'react';
import { landmarkDisplayColor } from './landmarkColor';
import { landmarksForRole } from './landmarkData';

const VideoDrawer = ({
  videoRef,
  boundingBoxes,
  fps,
  persons,
  tasks,
  selectedTask,
  style,
  displayWidth,
  displayHeight,
  screen = 'default',
  isPlaying,
  zoomLevel,
  videoWidth,
  videoHeight,
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

  const drawBoundingBoxes = useCallback((scaleRatio) => {
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
        const strokeThickness = 5 / scaleRatio
        ctx.lineWidth = strokeThickness;
        ctx.rect(x, y, width, height);
        ctx.stroke();

        const personIdx = persons.findIndex((p) => p.id === box.id);
        if (personIdx !== -1) {
          const label = String(personIdx + 1);
          const strokeThickness = ctx.lineWidth;

          ctx.save();
          ctx.fillStyle = "yellow";
          ctx.font = `bold ${Math.round(4 * strokeThickness)}px system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif`;
          ctx.textBaseline = "top";
          ctx.textAlign = "left";
          ctx.fillText(label, x + strokeThickness * 0.5, y + strokeThickness * 0.5);
          ctx.restore();
        }
      });
    }
  }, [boundingBoxes, persons]);

  const drawLandMarks = useCallback((scaleRatio, mediaTime) => {
    if (!tasks.length || selectedTask == null) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const currentTask = tasks[selectedTask];
    const landMarks = landmarksForRole(currentTask?.data, 'display');
    const landmarkFps = currentTask.data?.landmark_fps ?? fps;
    const startFrame = currentTask.data?.landmark_start_frame
      ?? Math.round(currentTask.start * landmarkFps);
    const frameIndex = Math.round(mediaTime * landmarkFps) - startFrame;
    if (
      frameIndex < 0 ||
      !landMarks ||
      frameIndex >= landMarks.length
    ) return;

    const joints2D = landMarks[frameIndex];
    // pre‐compute the crop offset
    if (canvas.width === 0 || canvas.height === 0) return;
    const radiusPx = 5 / scaleRatio
    
    joints2D.forEach((pt, j) => {
      if (!pt || pt.length < 2) return;
      const [lx, ly] = pt;
      const fill = landmarkDisplayColor(landmark_colors, frameIndex, j);
      ctx.fillStyle = fill;
      ctx.beginPath();
      ctx.arc(lx , ly , radiusPx, 0, 2 * Math.PI);
      ctx.fill();
    });
  }, [tasks, selectedTask, fps, landmark_colors]);


  // Modified drawFrame: we only draw bounding boxes when not in a taskBox time interval.
  const drawFrame = useCallback((currentTime) => {
      const video = videoRef.current;
      if (!video) return;
      const frameNumber = getFrameNumber(currentTime);
      // console.log("Drawer frame: " + frameNumber)
      lastDrawnFrame.current = frameNumber;
      currentFrame.current = frameNumber;

      // The native video element renders the pixels. This canvas is only an
      // overlay; copying video frames through canvas caused stale/frozen frames
      // in Chromium for some valid H.264 files.
      clearCanvas();

      // Check if currentTime is within any taskBox's time window.
      const inTaskTime = tasks.some((task) => currentTime >= task.start && currentTime <= task.end);
      const scaleRatio =  Math.min(
        displayWidth  / videoWidth,
        displayHeight / videoHeight
      ) * zoomLevel;
      if (screen === 'subject_resolution') {
        drawBoundingBoxes(scaleRatio);
      }

      if (screen === 'tasks' && !inTaskTime) {
        drawBoundingBoxes(scaleRatio);
      }

      if (screen === 'taskDetails' && isPlaying) {
        drawLandMarks(scaleRatio, currentTime);
      }
    },
    [videoRef, getFrameNumber, clearCanvas, drawBoundingBoxes, drawLandMarks, tasks,
      screen, isPlaying, zoomLevel, displayWidth, displayHeight, videoWidth, videoHeight]
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
    let cancelled = false;
    const render = (now, metadata) => {
      if (cancelled) return;
      drawFrame(metadata.mediaTime);
      if (!cancelled) {
        frameCallbackId = video.requestVideoFrameCallback(render);
      }
    };
  
    frameCallbackId = video.requestVideoFrameCallback(render);  
    return () => {
      cancelled = true;
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
  }, [persons, tasks, landmark_colors, selectedTask, screen, drawFrame, videoRef, isPlaying]);
  
  return (
    <canvas
      ref={canvasRef}
      style={style}
    />
  );
};

export default VideoDrawer;
