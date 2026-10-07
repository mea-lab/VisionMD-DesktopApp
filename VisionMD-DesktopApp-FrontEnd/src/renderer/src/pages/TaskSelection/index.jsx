//src/pages/TaskSelection/index.jsx
import { initializeTaskBox, patchTask } from './taskBoundingBox';
import VideoPlayer from '../../components/VideoPlayer/VideoPlayer';
import HeaderSection from './HeaderSection';
import { useEffect } from 'react';
import TaskSelectionTab from './TaskSelectionTab';
import TasksWaveForm from './TasksWaveForm';
import { useContext } from 'react';
import { VideoContext } from '../../contexts/VideoContext';
import { useNavigate } from 'react-router-dom';

const TaskSelection = () => {
  const {
    videoId,
    videoRef,
    persons,
    videoReady, setVideoReady,
    videoData, setVideoData,
    videoURL, setVideoURL,
    fileName, setFileName,
    boundingBoxes, setBoundingBoxes,
    fps, setFPS, frameCount,
    tasks, setTasks, 
    tasksReady, setTasksReady,
    taskTypeData, setTaskTypeData
  } = useContext(VideoContext);

  const navigate = useNavigate();
  useEffect(() => {
    if(!videoId) {
      navigate("/")
    }
  },[])

  const updateTaskWithBox = task => initializeTaskBox(task, boundingBoxes, fps);

  const onTaskCreate = newTask => {
    console.log("onTaskCreate running", newTask)
    setTasks(prev => [...prev, updateTaskWithBox(newTask)]);
  };

  const onTaskChange = (patch) => {
    setTasks(prev =>
      prev.map(t => {
        if (t.id !== patch.id) return t;
        return patchTask(t, patch, boundingBoxes, fps);
      })
    );
  };

  const onTaskDelete = deletedTask => {
    const newTasks = tasks.filter(task => task.id !== deletedTask.id);
    setTasks(newTasks);
  };

  const replaceTasksFromWaveform = replacementTasks => {
    setTasks(replacementTasks.map(updateTaskWithBox));
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
            frameCount={frameCount}
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
            frameCount={frameCount}
            boundingBoxes={boundingBoxes}
            persons={persons}
            tasks={tasks}
            moveToNextScreen={moveToNextScreen}
          />
          <TasksWaveForm
            tasks={tasks}
            setTasks={setTasks}
            onTaskCreate={onTaskCreate}
            onTaskChange={onTaskChange}
            onTasksReplace={replaceTasksFromWaveform}
            fps={fps}
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
