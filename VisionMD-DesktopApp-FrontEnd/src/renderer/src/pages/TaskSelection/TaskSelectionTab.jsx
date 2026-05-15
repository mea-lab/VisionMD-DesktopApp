//src/pages/TaskSelection/TaskSelectionTab.jsx
import React, { useState } from 'react';
import TaskList from './TaskList';
import Button from '@mui/material/Button';
import JSONUploadDialog from './JSONUploadDialog';

const TaskSelectionTab = ({
  tasks,
  setBoundingBoxes,
  setTasks,
  setFPS,
  onTaskChange,
  onTaskDelete,
  isVideoReady,
  videoRef,
  tasksReady,
  setTasksReady,
  resetTaskSelection,
  taskTypeData,
  setTaskTypeData,
}) => {
  const [openJsonUpload, setOpenJsonUpload] = useState(false);

  const getTasksFromtasks = curtasks => {
    const newTasks = [];
    for (let curTaskBox of curtasks) {
      let curTask = {
        id: curTaskBox?.id,
        start: curTaskBox?.start,
        end: curTaskBox?.end,
        name: curTaskBox?.name,
      };
      curTask = { ...curTask, ...curTaskBox };
      newTasks.push(curTask);
    }

    return newTasks;
  };
  
  const jsonFileHandle = (jsonFileUploaded, jsonContent) => {
    if (jsonFileUploaded && jsonContent !== null) {
      if (jsonContent.hasOwnProperty('boundingBoxes')) {
        //new json
        setBoundingBoxes(jsonContent['boundingBoxes']);
        setFPS(jsonContent['fps']);
        if (jsonContent.hasOwnProperty('tasks')) {
          const curtasks = jsonContent['tasks'];
          setTasks(curtasks);
          setTasks(getTasksFromtasks(curtasks));
        }
      } else {
        //old json
        const transformedData = jsonContent.map((item, index) => ({
          start: item.start,
          end: item.end,
          name: item.attributes.label,
          id: index + 1,
        }));
        setTasks(transformedData);
      }

      console.log('JSON file details captured and added.');
      setTasksReady(true);
    } else {
      setTasksReady(true);
    }
  };

  return (
    <div className="flex flex-col w-full h-full overflow-hidden px-2 py-4">
      {isVideoReady && tasks.length === 0  && (
        <div className="flex justify-center items-center h-full flex-col gap-4 w-full px-10 flex-1 py-4 overflow-y-auto rounded-lg bg-[#333338]">
          <div className='text-gray-100'>Setup the tasks</div>
          <button className='bg-[#1976d2] text-gray-100 rounded-md p-2' onClick={() => setOpenJsonUpload(true)}>
          Setup
        </button>
          <JSONUploadDialog
            dialogOpen={openJsonUpload}
            setDialogOpen={setOpenJsonUpload}
            handleJSONUpload={jsonFileHandle}
            videoRef={videoRef}
          />
        </div>
      )}
      {isVideoReady && tasks.length !== 0 && (
        <TaskList
          tasks={tasks}
          onTaskChange={onTaskChange}
          onTaskDelete={onTaskDelete}
          videoRef={videoRef}
          resetTaskSelection={resetTaskSelection}
          taskTypeData={taskTypeData}
          setTaskTypeData={setTaskTypeData}
        />
      )}
    </div>
  );
};

export default TaskSelectionTab;
