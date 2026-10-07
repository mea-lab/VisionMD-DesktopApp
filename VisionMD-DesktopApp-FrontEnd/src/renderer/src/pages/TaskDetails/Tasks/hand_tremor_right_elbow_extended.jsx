import FeatureTable from '../Tables/FeatureTable'
import TremorGraphs from '../Graphs/TremorGraphs';

const HandTremorRight = ({
  selectedTaskIndex,
  tasks,
  fileName,
  videoRef,
  startTime,
  endTime,
}) => {
 return(
      <div>
          {tasks[selectedTaskIndex] && (
            <div>
              <TremorGraphs
                selectedTaskIndex={selectedTaskIndex}
                tasks={tasks}
                fileName={fileName}
                videoRef={videoRef}
                startTime={startTime}
                endTime={endTime}
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

export default HandTremorRight;
