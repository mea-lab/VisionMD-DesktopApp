import React, { useRef, useEffect, useState } from 'react';

const ResizeHandles = ({ x, y, width, height, onResize, item, index, handleSize = 12.5, strokeThickness }) => {
  const handles = [
    {
      side: 'top',
      x: x + (width - width / 4) / 2,
      y: y - handleSize / 2,
      width: width / 4,
      height: handleSize,
      cursor: 'ns-resize'
    },
    {
      side: 'bottom',
      x: x + (width - width / 4) / 2,
      y: y + height - handleSize / 2,
      width: width / 4,
      height: handleSize,
      cursor: 'ns-resize'
    },
    {
      side: 'left',
      x: x - handleSize / 2,
      y: y + (height - height / 4) / 2,
      width: handleSize,
      height: height / 4,
      cursor: 'ew-resize'
    },
    {
      side: 'right',
      x: x + width - handleSize / 2,
      y: y + (height - height / 4) / 2,
      width: handleSize,
      height: height / 4,
      cursor: 'ew-resize'
    }
  ];

  return handles.map(handle => (
    <rect
      key={handle.side}
      x={handle.x}
      y={handle.y}
      width={handle.width}
      height={handle.height}
      fill="#4A8074"
      stroke="white"
      strokeWidth={strokeThickness/2}
      onPointerDown={(e) => onResize(e, item, index, handle.side)}
      style={{ cursor: handle.cursor }}
    />
  ));
};

const InteractiveOverlays = ({
  tasks,
  setTasks,
  fileName,
  zoomLevel,
  panOffset,
  videoWidth,
  videoHeight,
  screen,
  selectedTask,
  fps,
  isPlaying,
  videoRef,
  displayWidth,
  displayHeight,
}) => {
  const svgRef = useRef(null);
  const resizingTaskRef = useRef(null);
  const draggingTaskRef = useRef(null);
  const draggingLandmarkRef = useRef(null);
  const tasksRef = useRef(tasks);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [landMarkIndex, setLandMarkIndex] = useState(null);

  // Sync tasksRef with the tasks state.
  useEffect(() => {
    tasksRef.current = tasks;
  }, [tasks]);

  // Video frame callback to update the current frame and landmark index.
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    let frameCallbackId;
    const updateFrame = (now, metadata) => {
      const frame = Math.round(metadata.mediaTime * fps);
      // console.log("Interactive frame: " + frame)
      setCurrentFrame(frame);
      const offset = Math.round((tasks[selectedTask]?.start ?? 0) * fps);
      setLandMarkIndex(frame - offset);
      frameCallbackId = video.requestVideoFrameCallback(updateFrame);
    };
    frameCallbackId = video.requestVideoFrameCallback(updateFrame);
    return () => {
      if (video.cancelVideoFrameCallback) {
        video.cancelVideoFrameCallback(frameCallbackId);
      }
    };
  }, [videoRef, fps, isPlaying, selectedTask]);

  const getSVGPoint = (evt) => {
    const svg = svgRef.current;
    if (!svg) return { x: evt.clientX, y: evt.clientY };
    const point = svg.createSVGPoint();
    point.x = evt.clientX;
    point.y = evt.clientY;
    const ctm = svg.getScreenCTM();
    return ctm ? point.matrixTransform(ctm.inverse()) : { x: evt.clientX, y: evt.clientY };
  };

  // === Task box resizing and dragging functions ===
  const handleTaskResizeStart = (e, task, taskIndex, side) => {
    e.stopPropagation();
    e.preventDefault();
    const { x: startX, y: startY } = getSVGPoint(e);
    resizingTaskRef.current = {
      taskIndex,
      startX,
      startY,
      initialX: task.x,
      initialY: task.y,
      initialWidth: task.box_width,
      initialHeight: task.box_height,
      side,
    };
    window.addEventListener('pointermove', handleTaskResizeMove);
    window.addEventListener('pointerup', handleTaskResizeEnd);
  };

  const handleTaskResizeMove = (e) => {
    if (!resizingTaskRef.current) return;
    const { x, y } = getSVGPoint(e);
    const { startX, startY, initialX, initialY, initialWidth, initialHeight, side, taskIndex } =
      resizingTaskRef.current;
    let newX = initialX;
    let newY = initialY;
    let newWidth = initialWidth;
    let newHeight = initialHeight;
    const minSize = 10;
    const deltaX = x - startX;
    const deltaY = y - startY;
    if (side === 'top') {
      newHeight = Math.max(minSize, initialHeight - deltaY);
      newY = initialY + (initialHeight - newHeight);
    } else if (side === 'bottom') {
      newHeight = Math.max(minSize, initialHeight + deltaY);
    } else if (side === 'left') {
      newWidth = Math.max(minSize, initialWidth - deltaX);
      newX = initialX + (initialWidth - newWidth);
    } else if (side === 'right') {
      newWidth = Math.max(minSize, initialWidth + deltaX);
    }
    setTasks((prevBoxes) =>
      prevBoxes.map((task, idx) =>
        idx === taskIndex ? { ...task, x: newX, y: newY, box_width: newWidth, box_height: newHeight } : task
      )
    );
  };

  const handleTaskResizeEnd = () => {
    resizingTaskRef.current = null;
    window.removeEventListener('pointermove', handleTaskResizeMove);
    window.removeEventListener('pointerup', handleTaskResizeEnd);
  };

  const handleTaskDragStart = (e, task, taskIndex) => {
    e.stopPropagation();
    e.preventDefault();
    const { x, y } = getSVGPoint(e);
    draggingTaskRef.current = {
      taskIndex,
      startX: x,
      startY: y,
      initialX: task.x,
      initialY: task.y,
    };
    window.addEventListener('pointermove', handleTaskDragMove);
    window.addEventListener('pointerup', handleTaskDragEnd);
  };

  const handleTaskDragMove = (e) => {
    if (!draggingTaskRef.current) return;
    const { x, y } = getSVGPoint(e);
    const { startX, startY, initialX, initialY } = draggingTaskRef.current;
    const dx = x - startX;
    const dy = y - startY;
    const newX = initialX + dx;
    const newY = initialY + dy;
    setTasks((prevBoxes) =>
      prevBoxes.map((task, idx) =>
        idx === draggingTaskRef.current?.taskIndex?  { ...task, x: newX, y: newY } : task
      )
    );
  };

  const handleTaskDragEnd = () => {
    draggingTaskRef.current = null;
    window.removeEventListener('pointermove', handleTaskDragMove);
    window.removeEventListener('pointerup', handleTaskDragEnd);
  };

  // === Landmark dragging functions ===
  const handleLandmarkDragStart = (e, landmarkIdx) => {
    e.stopPropagation();
    e.preventDefault();
    const svgPoint = getSVGPoint(e);
    const taskBox = tasks[selectedTask];
    const currentLandmark = tasks[selectedTask].data.landMarks[landMarkIndex][landmarkIdx];
    const circleCenterX = currentLandmark[0] + taskBox.x;
    const circleCenterY = currentLandmark[1] + taskBox.y;
    const offsetX = svgPoint.x - circleCenterX;
    const offsetY = svgPoint.y - circleCenterY;
    draggingLandmarkRef.current = { landmarkIdx, offsetX, offsetY };
    window.addEventListener('pointermove', handleLandmarkDragMove);
    window.addEventListener('pointerup', handleLandmarkDragEnd);
  };

  const handleLandmarkDragMove = (e) => {
    if (!draggingLandmarkRef.current) return;
    const svgPoint = getSVGPoint(e);
    const { landmarkIdx, offsetX, offsetY } = draggingLandmarkRef.current;
    const taskBox = tasks[selectedTask];
    const newCircleCenterX = svgPoint.x - offsetX;
    const newCircleCenterY = svgPoint.y - offsetY;
    const newRelativeX = newCircleCenterX - taskBox.x;
    const newRelativeY = newCircleCenterY - taskBox.y;
    setTasks((prevTasks) => {
      const newTasks = [...prevTasks];
      const task = { ...newTasks[selectedTask] };
      const data = { ...task.data };
      const newLandmarks = data.landMarks.slice();
      const currentFrameLandmarks = newLandmarks[landMarkIndex].slice();
      currentFrameLandmarks[landmarkIdx] = [newRelativeX, newRelativeY];
      newLandmarks[landMarkIndex] = currentFrameLandmarks;
      data.landMarks = newLandmarks;
      task.data = data;
      newTasks[selectedTask] = task;
      // Update our ref immediately.
      tasksRef.current = newTasks;
      return newTasks;
    });
  };

  // Call the API once dragging is finished.
  const handleLandmarkDragEnd = async () => {
    window.removeEventListener('pointermove', handleLandmarkDragMove);
    window.removeEventListener('pointerup', handleLandmarkDragEnd);
    draggingLandmarkRef.current = null;

    const updatedLandmarks = tasksRef.current[selectedTask].data.landMarks;
    

    try {
      const start = tasksRef.current[selectedTask].start;
      const end = tasksRef.current[selectedTask].end;
      const data = tasksRef.current[selectedTask].data;
      const currentTaskName = tasksRef.current[selectedTask].name;
      const jsonData = JSON.stringify({
        task_name: currentTaskName,
        start_time: start,
        end_time: end,
        fps,
        landmarks: updatedLandmarks,
        ...data
      });
      console.log("Uploaded Json", JSON.parse(jsonData));
      const uploadData = new FormData();
      uploadData.append('json_data', jsonData);
      const response = await fetch('http://localhost:8000/api/update_landmarks/', {
        method: 'POST',
        body: uploadData,
      });
      if (response.ok) {
        const updatedData = await response.json();
        handleProcessing(true, updatedData);
      } else {
        throw new Error('Server responded with an error!');
      }
    } catch (error) {
      console.error('Failed to update landmarks:', error);
    }
  };

  const handleProcessing = (jsonFileUploaded, jsonContent) => {
    console.log("Return Data", jsonContent);
    if (jsonFileUploaded && jsonContent) {
      const safeFileName = fileName.replace(/\.[^/.]+$/, '');
      setTasks(prev => {
        const newTasks = [...prev];
        newTasks[selectedTask] = { ...newTasks[selectedTask], data: { ...jsonContent, fileName: safeFileName } };
        return newTasks;
      });
    }
  };

  let taskToRender = null;
  let taskIndex = -1;
  if (screen === 'tasks') {
    const currentTime = currentFrame / fps;
    taskIndex = tasks.findIndex((t) => currentTime >= t.start && currentTime <= t.end);
    if (taskIndex !== -1) {
      taskToRender = tasks[taskIndex];
    }
  } else if (screen === 'taskDetails') {
    if (selectedTask != null && tasks[selectedTask]) {
      taskIndex = selectedTask;
      taskToRender = tasks[selectedTask];
    }
  }

  const strokeThickness = 5 / Math.min(
    displayWidth  / videoWidth,
    displayHeight / videoHeight
  ) / zoomLevel;
  const landmarkRadius = 5 / Math.min(
    displayWidth  / videoWidth,
    displayHeight / videoHeight
  ) / zoomLevel;
  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${videoWidth} ${videoHeight}`}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        transform: `scale(${zoomLevel}) translate(${panOffset.x / zoomLevel}px, ${panOffset.y / zoomLevel}px)`,
        transformOrigin: 'center center',
        pointerEvents: 'all',
      }}
    >
      {((screen === 'tasks' || screen === 'taskDetails') && taskToRender) && (
        <g key={`task-${taskIndex}`}>
          <rect
            x={taskToRender.x}
            y={taskToRender.y}
            width={taskToRender.box_width}
            height={taskToRender.box_height}
            stroke="green"
            strokeWidth={strokeThickness}
            fill="none"
            pointerEvents="stroke"
            onPointerDown={(!isPlaying && screen === 'tasks') ? (e) => handleTaskDragStart(e, taskToRender, taskIndex) : undefined}
            style={{ cursor: (!isPlaying && screen === 'tasks') ? 'move' : 'default' }}
          />
          <text
            x={taskToRender.x + strokeThickness * 0.5}
            y={taskToRender.y + strokeThickness * 0.5}
            fontSize={4 * strokeThickness}
            fontWeight="700"
            textAnchor="start"
            dominantBaseline="hanging"
            fill="yellow"
          >
            {taskIndex + 1}
          </text>
          {(!isPlaying && screen === 'tasks') && (
            <ResizeHandles
              x={taskToRender.x}
              y={taskToRender.y}
              width={taskToRender.box_width}
              height={taskToRender.box_height}
              handleSize={strokeThickness}
              onResize={handleTaskResizeStart}
              item={taskToRender}
              index={taskIndex}
              strokeThickness={strokeThickness}
            />
          )}
        </g>
      )}


      {/* Render interactive landmarks when paused */}
      {(!isPlaying && landMarkIndex != null && tasks?.[selectedTask]?.data?.landMarks?.[landMarkIndex]) && (
        <g className="landmarks-group">
          {(() => {
            const colors3D = tasks[selectedTask].data.landmark_colors;
            return tasks[selectedTask].data.landMarks[landMarkIndex].map((point, idx) => {
              const [px, py] = point;
              let fillColor = 'red';
              if (
                Array.isArray(colors3D) &&
                colors3D[landMarkIndex] &&
                Array.isArray(colors3D[landMarkIndex][idx])
              ) {
                const [r, g, b] = colors3D[landMarkIndex][idx];
                fillColor = `rgb(${r}, ${g}, ${b})`;
              }
              return (
                <circle
                  key={`landmark-${idx}`}
                  cx={px}
                  cy={py}
                  r={landmarkRadius}
                  fill={fillColor}
                  stroke="white"
                  strokeWidth={strokeThickness/2}
                  onPointerDown={(e) => handleLandmarkDragStart(e, idx)}
                  style={{ cursor: 'move' }}
                />
              );
            });
          })()}
        </g>
      )}
    </svg>
  );
};

export default InteractiveOverlays;
