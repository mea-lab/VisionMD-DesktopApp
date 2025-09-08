//src/pages/TaskSelection/TaskList.jsx
import { useState } from 'react';
import { taskOptions } from '../../constants/taskOptions'; 
import Default from './Tasks/default'


const Header = ({ resetTaskSelection }) => {
  return (
    <div className="flex flex-col border-b-2 py-2 text-gray-100 border-zinc-500">
      Task Selection
    </div>
  );
};

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
}) => {
  const [options, setOptions] = useState(taskOptions);

  const onFieldChange = (newValue, fieldName, task) => {
    let newTask = { ...task };
    if(newTask[fieldName] && newTask[fieldName] == newValue) return;
    
    newTask[fieldName] =
      fieldName === 'start' || fieldName === 'end'
        ? Number(Number(newValue).toFixed(3))
        : newValue;
    onTaskChange(newTask);
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
      <Header resetTaskSelection={resetTaskSelection} />

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
                    key={index}
                    task={task}
                    taskTypeIndex={taskTypeIndex}
                    onFieldChange={onFieldChange}
                    onTaskDelete={onTaskDelete}
                    onTimeMark={onTimeMark}
                    onTimeClick={onTimeClick}
                    options={options}
                    setOptions={setOptions}
                  />
                );
              } else {
                return (
                  <TaskComponent
                    key={index}
                    task={task}
                    taskTypeIndex={taskTypeIndex}
                    onFieldChange={onFieldChange}
                    onTaskDelete={onTaskDelete}
                    onTimeMark={onTimeMark}
                    onTimeClick={onTimeClick}
                    options={options}
                    setOptions={setOptions}
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