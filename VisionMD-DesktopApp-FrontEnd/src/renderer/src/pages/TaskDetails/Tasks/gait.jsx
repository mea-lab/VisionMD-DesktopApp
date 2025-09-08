import {useState, useEffect} from 'react'
import ScatterPlot from '../Tables/ScatterPlot';
import FeatureTable from '../Tables/FeatureTable'
import GaitGraphs from '../Graphs/GaitGraphs';

const Gait = ({
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
              <GaitGraphs
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

export default Gait;