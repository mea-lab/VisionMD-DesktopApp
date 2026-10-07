import FeatureTable from '../Tables/FeatureTable'
import GaitGraphs from '../Graphs/GaitGraphs';
import GaitSegmentsPanel from '../Graphs/GaitSegmentsPanel';

const Gait = ({
  selectedTaskIndex,
  tasks,
  setTasks,
  fileName,
  videoRef,
}) => {
 return(
      <div>
          {tasks[selectedTaskIndex] && (
            <div>
              <GaitSegmentsPanel
                selectedTaskIndex={selectedTaskIndex}
                tasks={tasks}
                setTasks={setTasks}
                videoRef={videoRef}
              />
              <GaitGraphs
                selectedTaskIndex={selectedTaskIndex}
                tasks={tasks}
                videoRef={videoRef}
              />
              <FeatureTable
                selectedTaskIndex={selectedTaskIndex}
                tasks={tasks}
                fileName={fileName}
              />
            </div>
            )}
      </div>
  )
}

export default Gait;
