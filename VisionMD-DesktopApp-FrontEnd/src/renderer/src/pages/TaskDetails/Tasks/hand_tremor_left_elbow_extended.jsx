import {useState, useEffect} from 'react'
import ScatterPlot from '../Tables/ScatterPlot';
import FeatureTable from '../Tables/FeatureTable'
import TremorGraphs from '../Graphs/TremorGraphs';

const HandTremorLeft = ({
  selectedTaskIndex,
  tasks,
  setTasks,
  fileName,
  videoRef,
  startTime,
  endTime,
  handleJSONUpload,
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

export default HandTremorLeft;