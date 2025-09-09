//src/pages/TaskSelection/TaskList.jsx
import { useState } from 'react';
import { taskOptions } from '../../constants/taskOptions'; 
import Default from './Tasks/default'

const selectedTaskFiles = Object.fromEntries(
  taskOptions.map(({ value }) => {
    const fileName = value.toLowerCase().replace(/\s+/g, '_');
    const module = import.meta.glob('./Tasks/*.jsx', { eager: true });
    const match = Object.entries(module).find(([path]) =>
      path.endsWith(`/${fileName}.jsx`)
    );
    return [value, match ? match[1].default : null];
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
    onTaskChange({ id: task.id, [fieldName]: value });
  };

  const onTimeMark = (fieldName, task) => {
    let newTask = { ...task };
    newTask[fieldName] = Number(
      Number(videoRef.current?.currentTime || 0).toFixed(3),
    );
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
                  <Default
                    key={task.id}
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
                );
              } else {
                return (
                  <TaskComponent
                    key={task.id}
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