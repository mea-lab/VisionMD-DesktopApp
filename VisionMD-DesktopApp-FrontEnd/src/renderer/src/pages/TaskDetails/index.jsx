//src/pages/TaskDetails/index.jsx
import React, {
  useContext,
  useEffect,
  useRef,
  useState,
  Suspense,
} from 'react';

import { useNavigate } from 'react-router-dom';

import VideoPlayer from '../../components/VideoPlayer/VideoPlayer';
import { VideoContext } from '../../contexts/VideoContext';
import HeaderSection from './HeaderSection';
import JSONUploadDialog from './JSONUploadDialog';

import RestartAltIcon from '@mui/icons-material/RestartAlt';
import CloudDownloadIcon from '@mui/icons-material/CloudDownload';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';

const TaskDetails = () => {
  const {
    videoId,
    videoReady,
    setVideoReady,
    videoData,
    setVideoData,
    videoURL,
    videoRef,
    fileName,
    boundingBoxes,
    setBoundingBoxes,
    fps,
    tasks,
    setTasks,
    persons,
  } = useContext(VideoContext);
  

  const [openJsonUpload, setOpenJsonUpload] = useState(false);
  const [analyzingAll, setAnalyzingAll] = useState(false);
  const [selectedTask, setSelectedTask] = useState(0);
  const [TaskModule, setTaskModule] = useState(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [taskErrors, setTaskErrors] = useState({});
  const dropdownRef = useRef(null);

  console.log("Tasks", tasks)
  console.log("taskErrors",taskErrors)

  const navigate = useNavigate();

  useEffect(() => {
    const handleClickOutside = e => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    };
    if (dropdownOpen) document.addEventListener('mousedown', handleClickOutside);
    return () =>
      document.removeEventListener('mousedown', handleClickOutside);
  }, [dropdownOpen]);

  /* load per-task module */
  useEffect(() => {
    if (!videoReady) return;
    if (!tasks || !tasks[selectedTask]) return;
    if (!videoId) navigate('/');

    const task = tasks[selectedTask];
    const taskName = task.name;
    const fileNameSafe = taskName.toLowerCase().split(' ').join('_');

    import(`./Tasks/${fileNameSafe}.jsx`)
      .then(mod => {
        setTaskModule(() => mod.default);
      })
      .catch(err => {
        console.error(`Couldn’t load task module ${taskName}:`, err);
        setTaskModule(null);
      });
  }, [selectedTask, videoReady, videoRef]);

  const handleProcessing = (jsonFileUploaded, jsonContent) => {
    if (jsonFileUploaded && jsonContent) {
      setTasks(prev => {
        const newTasks = [...prev];
        newTasks[selectedTask] = {
          ...newTasks[selectedTask],
          data: { ...jsonContent },
        };
        return newTasks;
      });
    }
  };

  const resetTask = () => {
    setTasks(prev => {
      const newTasks = [...prev];
      newTasks[selectedTask] = { ...newTasks[selectedTask], data: null };
      return newTasks;
    });
    
    const currentTask = tasks?.[selectedTask];
    const currentTaskId = currentTask?.id;

    setTaskErrors(prev => {
      const { [currentTaskId]: _omit, ...rest } = prev;
      return rest;
    });
  };

  
  const clearTaskError = (taskId) => {
    setTaskErrors(prev => {
      const { [taskId]: _omit, ...rest } = prev;
      return rest;
    });
  };

  const autoAnalyzeTask = async taskId => {
    try {
      const videoURL = videoRef.current.src;
      const videoBlob = await fetch(videoURL).then(r => r.blob());
      const taskData = tasks.find(t => t.id === taskId);
      if (!taskData) throw new Error(`Task with id ${taskId} not found`);

      const chosenTaskBox = tasks.find(box => box.id === taskData.id);
      const taskBoxCords = {
        x: chosenTaskBox.x,
        y: chosenTaskBox.y,
        width: chosenTaskBox.box_width,
        height: chosenTaskBox.box_height,
      };

      const subjectBoundingBoxes = boundingBoxes.map(({ frameNumber, data }) => ({
        frameNumber,
        data: data.filter(item => item.Subject === true),
      }));

      const { start, end, name, data, ...otherTaskFields } = taskData;
      let jsonData = {
        boundingBox: taskBoxCords,
        task_name: name,
        start_time: start,
        end_time: end,
        fps,
        subject_bounding_boxes: subjectBoundingBoxes,
        ...otherTaskFields,
      };
      jsonData = JSON.stringify(jsonData);

      const form = new FormData();
      form.append("video", videoBlob);
      form.append("json_data", jsonData);

      const sanitizedTaskName = name
        .replace(/[^a-zA-Z0-9]+/g, " ")
        .split(" ")
        .filter(Boolean)
        .map(w => w.toLowerCase())
        .join("_");

      const apiURL = `http://localhost:8000/api/${sanitizedTaskName}/?id=${videoId}`;

      const res = await fetch(apiURL, { method: "POST", body: form });
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`${name} failed (${res.status})${text ? `: ${text}` : ""}`);
      }

      const result = await res.json();
      const safeFileName = fileName.replace(/\.[^/.]+$/, "");

      setTasks(prev =>
        prev.map(t =>
          t.id === taskId
            ? { ...t, data: { ...result, fileName: safeFileName } }
            : t
        )
      );

      setTaskErrors(prev => {
        const { [taskId]: _remove, ...rest } = prev;
        return rest;
      });

      return true;
    } catch (err) {
      console.error(err);
      setTaskErrors(prev => ({
        ...prev,
        [taskId]: err?.message || "Unknown error",
      }));
      return false;
    }
  };

  const analyzeAllTasks = async () => {
    setTaskErrors({});
    setAnalyzingAll(true);

    for (const task of tasks) {
      if (!task?.data) {
        await autoAnalyzeTask(task.id);
      }
    }
    setAnalyzingAll(false);
  };

  const DownloadCurrentTask = () => {
    const currentTask = tasks[selectedTask];
    const fileData = currentTask.data;
    const jsonStr = JSON.stringify(fileData);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const href = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = href;
    link.download = `${fileName.replace(/\.[^/.]+$/, '')}_${currentTask.name}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(href);
  };

  const downloadAllTasks = () => {
    tasks.forEach(task => {
      if (!task?.data) return;
      const jsonStr = JSON.stringify(task.data);
      const blob = new Blob([jsonStr], { type: 'application/json' });
      const href = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = href;
      link.download = `${fileName.replace(/\.[^/.]+$/, '')}_${task.name}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(href);
    });
  };

  const btn =
    'bg-[#1976d2] hover:bg-[#1565c0] text-white px-3 py-1 ' +
    'rounded-md inline-flex items-center gap-1 ' +
    'disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap';

  const currentTask = tasks?.[selectedTask];
  const currentTaskId = currentTask?.id;
  const currentTaskError = currentTaskId ? taskErrors[currentTaskId] : null;
  const hasData = Boolean(currentTask?.data);

  return (
    <div className="flex flex-col h-screen">
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 min-w-[50%] h-full bg-slate-900">
          <VideoPlayer
            videoURL={videoURL}
            videoData={videoData}
            videoRef={videoRef}
            screen="taskDetails"
            boundingBoxes={boundingBoxes}
            setBoundingBoxes={setBoundingBoxes}
            fps={fps}
            persons={persons}
            setVideoReady={setVideoReady}
            setVideoData={setVideoData}
            fileName={fileName}
            landMarks={tasks[selectedTask]?.data?.landMarks}
            selectedTask={selectedTask}
            tasks={tasks}
            setTasks={setTasks}
          />
        </div>

        <div className="flex-1 flex flex-col min-w-[50%] border-l border-l-zinc-600 bg-zinc-800 overflow-y-auto">
          <HeaderSection
            title="Task Details"
            isVideoReady={videoReady}
            fileName={fileName}
            fps={fps}
            boundingBoxes={boundingBoxes}
          />

          <div className="flex items-center justify-center gap-2 mt-2 mb-4">
            <div className="text-gray-100">Current task - </div>

            {/* task selector */}
            <select
              className="border border-zinc-600 bg-zinc-800 text-gray-100 rounded-md px-2 py-1"
              value={selectedTask}
              onChange={e => setSelectedTask(Number(e.target.value))}
            >
              {tasks.map((task, index) => (
                <option key={index} value={index}>
                  {task.id}. {task.name}
                </option>
              ))}
            </select>

            {/* Reset */}
            <button className={btn} onClick={resetTask}>
              <RestartAltIcon fontSize="small" />
              Reset
            </button>

            {/*  Split Download button */}
            <div className="relative inline-flex" ref={dropdownRef}>
              {/* main download */}
              <button
                className={`${btn} rounded-r-none border-r border-blue-800`}
                onClick={DownloadCurrentTask}
                disabled={!tasks[selectedTask]?.data}
              >
                <CloudDownloadIcon fontSize="small" />
                Download
              </button>

              {/* arrow trigger */}
              <button
                className={`${btn} rounded-l-none px-2`}
                onClick={() => setDropdownOpen(prev => !prev)}
                disabled={!tasks.some(t => t?.data)}
              >
                <ArrowDropDownIcon fontSize="small" />
              </button>

              {/* dropdown */}
              {dropdownOpen && (
                <div className="absolute right-0 top-full mt-1 w-40 bg-white border border-gray-200 rounded-md shadow-md z-20">
                  <button
                    className="w-full text-center px-2 py-1 hover:bg-gray-100 disabled:opacity-50"
                    onClick={() => {
                      downloadAllTasks();
                      setDropdownOpen(false);
                    }}
                    disabled={!tasks.some(t => t?.data)}
                  >
                    Download All
                  </button>
                </div>
              )}
            </div>

            {/* Analyze All */}
            <button
              className={btn}
              onClick={analyzeAllTasks}
              disabled={analyzingAll || !tasks.some(t => t.data == null)}
            >
              Analyze All
            </button>
          </div>

          <div className="flex-1 py-4 px-10 overflow-y-auto text-gray-100">
            {currentTaskError ? (
              <div className="flex justify-center items-center h-full flex-col gap-4">
                <div> Analyze the task </div>
                <button
                  className={`${btn} text-base`}
                  onClick={() => {
                    clearTaskError(currentTaskId);
                    setOpenJsonUpload(true);
                  }}
                >
                  Analyze
                </button>
                <div className="max-h-48 overflow-y-auto">
                  <Typography color="error">{currentTaskError}</Typography>
                </div>
              </div>
            ) : hasData ? (
              TaskModule ? (
                <TaskModule
                  selectedTaskIndex={selectedTask}
                  tasks={tasks}
                  setTasks={setTasks}
                  fileName={fileName}
                  videoRef={videoRef}
                  startTime={currentTask.start}
                  endTime={currentTask.end}
                  handleJSONUpload={handleProcessing}
                />
              ) : (
                <div className="flex justify-center items-center h-full">
                  Loading task view…
                </div>
              )
            ) : analyzingAll ? (
              <div className="flex justify-center items-center h-full flex-col gap-4">
                <div>Analyzing task...</div>
                <CircularProgress size={64} sx={{ color: '#2563eb' }} />
              </div>
            ) : (
              <div className="flex justify-center items-center h-full flex-col gap-4">
                <div>Analyze the task</div>
                <button
                  className={`${btn} text-base`}
                  onClick={() => setOpenJsonUpload(true)}
                >
                  Analyze
                </button>
              </div>
            )}
          </div>

          {/* Keep the dialog mounted so it can open from any state */}
          <JSONUploadDialog
            dialogOpen={openJsonUpload}
            fps={fps}
            setDialogOpen={setOpenJsonUpload}
            handleJSONUpload={handleProcessing}
            boundingBoxes={boundingBoxes}
            videoRef={videoRef}
            tasks={tasks}
            selectedTask={selectedTask}
            analyzingAll={analyzingAll}
          />
        </div>
      </div>
    </div>
  );
};


export default TaskDetails;
