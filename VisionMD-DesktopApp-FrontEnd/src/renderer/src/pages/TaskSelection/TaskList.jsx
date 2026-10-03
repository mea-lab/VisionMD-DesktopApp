//src/pages/TaskSelection/TaskList.jsx
import { lazy, Suspense, useState } from 'react';
import isEqual from 'lodash/isEqual';
import { taskOptions } from '../../constants/taskOptions'; 
import Default from './Tasks/default'

const taskSelectionLoaders = import.meta.glob('./Tasks/*.jsx');
const selectedTaskFiles = Object.fromEntries(
  taskOptions.map(({ value }) => {
    const fileName = value.toLowerCase().replace(/\s+/g, '_');
    const match = Object.entries(taskSelectionLoaders).find(([path]) =>
      path.endsWith(`/${fileName}.jsx`)
    );
    return [value, match ? lazy(match[1]) : null];
  }).filter(([_, component]) => component)
);

const TaskList = ({
  tasks,
  onTaskChange,
  onTaskDelete,
  videoRef,
  resetTaskSelection,
  taskTypeData,
  setTaskTypeData,
}) => {
  const [options, setOptions] = useState(taskOptions);


  const onFieldChange = (newValue, fieldName, task) => {
    if (newValue === null || (Array.isArray(newValue) && newValue.flat().every(v => v === null))) {
      return;
    }
    const value =
      fieldName === 'start' || fieldName === 'end'
        ? Number(Number(newValue).toFixed(3))
        : newValue;
    if (isEqual(task?.[fieldName], value)) {
      return;
    }
    const changingWindow = fieldName === 'start' || fieldName === 'end';
    onTaskChange({
      id: task.id,
      [fieldName]: value,
      // A manually edited boundary is no longer the full-video selection.
      ...(changingWindow && task.full_video
        ? {
            full_video: false,
            manual_range: {
              start: fieldName === 'start' ? value : task.start,
              end: fieldName === 'end' ? value : task.end,
            },
          }
        : {}),
      data: null,
    });
  };

  const onTimeMark = (fieldName, task) => {
    let newTask = { ...task };
    newTask[fieldName] = Number(
      Number(videoRef.current?.currentTime || 0).toFixed(3),
    );
    // Marking a boundary manually turns a full-video task back into a custom range.
    if (task.full_video) {
      newTask.full_video = false;
      newTask.manual_range = { start: newTask.start, end: newTask.end };
    }
    newTask.data = null;
    onTaskChange(newTask);
  };

  const onTimeClick = time => {
    if (videoRef.current) videoRef.current.currentTime = time;
  };

  return (
    <div className="flex flex-col gap-2 p-4 py-2 h-full rounded-lg bg-[#333338] shadow-inner">
      <div className="flex flex-col border-b-2 py-2 text-gray-100 border-zinc-500">
        Task Selection
      </div>

      <div className="flex flex-col overflow-y-auto overflow-x-hidden">
        {tasks.length > 0 ? (
          (() => {
            const typeCounts = {};
            
            return tasks.map((task, index) => {
              const taskType = task.name;
              const TaskComponent = selectedTaskFiles[taskType];
              const taskTypeIndex = typeCounts[taskType] ?? 0;
              typeCounts[taskType] = taskTypeIndex + 1;
            
              if (!TaskComponent) {
                return (
                  <div key={task.id}>
                  <Default
                    task={task}
                    taskTypeIndex={taskTypeIndex}
                    onFieldChange={onFieldChange}
                    onTaskDelete={onTaskDelete}
                    onTimeMark={onTimeMark}
                    onTimeClick={onTimeClick}
                    options={options}
                    setOptions={setOptions}
                    taskGlobals={taskTypeData[task.name] || {}}
                    setTaskGlobals={(updates) =>
                      setTaskTypeData(prev => ({
                        ...prev,
                        [task.name]: { ...prev[task.name], ...updates }
                    }))
                    }
                  />
                  </div>
                );
              } else {
                return (
                  <div key={task.id}>
                  <Suspense fallback={<div className="p-4 text-gray-400">Loading task controls…</div>}>
                    <TaskComponent
                    task={task}
                    taskTypeIndex={taskTypeIndex}
                    onFieldChange={onFieldChange}
                    onTaskDelete={onTaskDelete}
                    onTimeMark={onTimeMark}
                    onTimeClick={onTimeClick}
                    options={options}
                    setOptions={setOptions}
                    taskGlobals={taskTypeData[task.name] || {}}
                    setTaskGlobals={(updates) =>
                      setTaskTypeData(prev => ({
                        ...prev,
                        [task.name]: { ...prev[task.name], ...updates }
                    }))
                    }
                    />
                  </Suspense>
                  </div>
                );
              }
            });
          })()
        ) : (
          <div className="text-center text-gray-100 py-4">No tasks added yet</div>
        )}
      </div>
    </div>
  );
};

export default TaskList;
