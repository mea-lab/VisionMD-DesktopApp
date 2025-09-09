//src/pages/TaskSelection/index.jsx
import VideoPlayer from '../../components/VideoPlayer/VideoPlayer';
import HeaderSection from './HeaderSection';
import { useEffect, useRef, useState } from 'react';
import TaskSelectionTab from './TaskSelectionTab';
import TasksWaveForm from './TasksWaveForm';
import { useContext } from 'react';
import { VideoContext } from '../../contexts/VideoContext';
import { useNavigate } from 'react-router-dom';

const TaskSelection = () => {
  const {
    videoId, videoReady, setVideoReady, videoData, setVideoData, videoURL, setVideoURL,
    videoRef, fileName, setFileName, boundingBoxes, setBoundingBoxes,
    fps, setFPS, setTasks, tasks, tasksReady, setTasksReady,
    persons, taskTypeData, setTaskTypeData
  } = useContext(VideoContext);

  const navigate = useNavigate();
  if (!videoId) {
    navigate("/")
  }

  const updateTaskWithBox = task => {
    const startFrame = Math.ceil(task.start * fps);
    const endFrame = Math.floor(task.end * fps);

    const regionBoxes = boundingBoxes
      .filter(({ frameNumber }) => frameNumber >= startFrame && frameNumber <= endFrame)
      .map(({ frameNumber, data }) => ({
        frameNumber,
        data: data.filter(item => item.Subject === true)
      }))
      .filter(({ data }) => data.length > 0);

    let minX = Infinity,
      minY = Infinity,
      maxX = -Infinity,
      maxY = -Infinity;

    regionBoxes.forEach(box => {
      box.data.forEach(({ x, y, width, height }) => {
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x + width);
        maxY = Math.max(maxY, y + height);
      });
    });

    return {
      ...task,
      x: minX,
      y: minY,
      box_width: maxX - minX,
      box_height: maxY - minY,
    };
  };


  const onTaskCreate = newTask => {
    console.log("onTaskCreate running", newTask)
    setTasks(prev => [...prev, updateTaskWithBox(newTask)]);
  };

  const onTaskChange = (patch) => {
    setTasks(prev =>
      prev.map(t => {
        if (t.id !== patch.id) return t;
        const merged = { ...t, ...patch };
        return { ...updateTaskWithBox(merged) };
      })
    );
  };

  const onTaskDelete = deletedTask => {
    const newTasks = tasks.filter(task => task.id !== deletedTask.id);
    setTasks(newTasks);
  };

  const resetTaskSelection = () => {
    setTasksReady(false);
    setTasks([]);
  };

  const moveToNextScreen = () => {
    navigate("/taskdetails");
  };

  return (
    <div className="flex flex-col h-screen">
      <div className="flex overflow-hidden">
        <div className="flex w-1/2 h-screen">
          <VideoPlayer
            videoURL={videoURL}
            setVideoURL={setVideoURL}
            screen={'tasks'}
            videoRef={videoRef}
            boundingBoxes={boundingBoxes}
            fps={fps}
            persons={persons}
            setVideoReady={setVideoReady}
            setVideoData={setVideoData}
            fileName={fileName}
            setFileName={setFileName}
            videoData={videoData}
            tasks={tasks}
            setTasks={setTasks}
          />
        </div>
        <div className="flex flex-col w-1/2 h-full border-l border-l-zinc-600 bg-zinc-800">
          <HeaderSection
            title={'Task Selection'}
            isVideoReady={videoReady}
            fileName={fileName}
            fps={fps}
            boundingBoxes={boundingBoxes}
            tasks={tasks}
            moveToNextScreen={moveToNextScreen}
          />
          <TasksWaveForm
            tasks={tasks}
            setTasks={setTasks}
            onTaskCreate={onTaskCreate}
            onTaskChange={onTaskChange}
            videoRef={videoRef}
            isVideoReady={videoReady}
            tasksReady={tasksReady}
            setTasksReady={setTasksReady}
          />
          <TaskSelectionTab
            setTasks={setTasks}
            tasksReady={tasksReady}
            setBoundingBoxes={setBoundingBoxes}
            setFPS={setFPS}
            tasks={tasks}
            onTaskChange={onTaskChange}
            onTaskDelete={onTaskDelete}
            isVideoReady={videoReady}
            videoRef={videoRef}
            taskReady={tasksReady}
            setTasksReady={setTasksReady}
            resetTaskSelection={resetTaskSelection}
            taskTypeData={taskTypeData}
            setTaskTypeData={setTaskTypeData}
          />
        </div>
      </div>
    </div>
  );
};

export default TaskSelection;
