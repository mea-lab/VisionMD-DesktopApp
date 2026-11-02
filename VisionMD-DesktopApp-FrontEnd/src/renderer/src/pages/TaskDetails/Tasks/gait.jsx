import FeatureTable from '../Tables/FeatureTable'
import GaitGraphs from '../Graphs/GaitGraphs';
import GaitSegmentsPanel from '../Graphs/GaitSegmentsPanel';

const overallFeatures = [
  'Average velocity', 'Average cadence', 'Average step length', 'Average stride length',
  'Average step time', 'Average stride time', 'Average stance time', 'Average swing time',
  'Step width', 'Step-width asymmetry (%)', 'Arm swing', 'Arm-swing amplitude asymmetry (%)',
  'Arm swing mean speed (m/s)', 'Arm swing P95 speed (m/s)', 'Arm swing correlation',
  'Torso medial-lateral trunk motion ROM', 'Torso medial-lateral mean speed (m/s)',
  'Turn duration (s)', 'Turn mean angular speed (deg/s)',
];
const additionalSideFeatures = [
  'Average step length left', 'Average step length right',
  'Average step time left', 'Average step time right',
  'Average velocity left', 'Average velocity right',
  'Average stance time left', 'Average stance time right',
  'Average swing time left', 'Average swing time right',
];
const gaitFeatureSections = [
  { title: 'Overall measures', features: overallFeatures },
  { title: 'Side-specific measures',
    features: [
      'Arm swing left', 'Arm swing right', 'Arm swing mean speed left (m/s)',
      'Arm swing mean speed right (m/s)', 'Arm swing P95 speed left (m/s)', 'Arm swing P95 speed right (m/s)',
      ...additionalSideFeatures,
    ],
  },
];

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
                includeUnavailable
                featureSections={gaitFeatureSections}
              />
            </div>
            )}
      </div>
  )
}

export default Gait;
