// Share gait's camera editor, height input, timing and subject-selection controls.
import Gait from './gait';

export default function SitToStand(props) {
  return <div>
    <Gait {...props} />
    {props.taskTypeIndex === 0 && <p className="mb-4 px-4 text-sm text-gray-300">Frontal single rise: include a seated baseline and the final standing posture. Keep the head, feet and arms visible. Heights and camera settings are retained; distances currently use a body-size reference. Review hand use in the video.</p>}
  </div>;
}
