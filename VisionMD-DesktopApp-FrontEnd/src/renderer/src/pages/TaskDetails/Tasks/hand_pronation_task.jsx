import ScatterPlot from '../Tables/ScatterPlot';
import WavePlotEditable from '../Graphs/WavePlotEditable';

/** Result view shared by both P/S sides.  The trace is an angular signal. */
const HandPronationTask = props => {
  const { selectedTaskIndex, tasks, setTasks, fileName, videoRef, startTime, endTime, handleJSONUpload } = props;
  const data = tasks[selectedTaskIndex]?.data;
  return (
    <div className="flex flex-col overflow-auto">
      <div className="pt-2 border-b border-gray-300">
        {data?.linePlot && <WavePlotEditable selectedTaskIndex={selectedTaskIndex} tasks={tasks} setTasks={setTasks} videoRef={videoRef} startTime={startTime} endTime={endTime} handleJSONUpload={handleJSONUpload} />}
      </div>
      <div className="pt-6">
        {data?.radarTable && <ScatterPlot selectedTaskIndex={selectedTaskIndex} tasks={tasks} fileName={fileName} />}
      </div>
    </div>
  );
};

export default HandPronationTask;
