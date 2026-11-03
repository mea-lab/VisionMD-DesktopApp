import FeatureTable from '../Tables/FeatureTable';
import SitToStandGraphs from '../Graphs/SitToStandGraphs';

export default function SitToStand(props) {
  const data = props.tasks?.[props.selectedTaskIndex]?.data;
  const metricOrder = data?.sit_to_stand?.quality?.metric_scaling === 'height_calibrated_3d' ? [
    'Central ascent time 10–90% (s)', 'Preparation to pelvic movement end (s)', 'Preparation lead-in (s)',
    'Pelvis excursion (cm)', 'Lateral pelvis range (cm)', 'Mean ascent speed (cm/s)', 'P95 ascent speed (cm/s)',
    'Ascent velocity coefficient of variation', 'Trunk lateral angular range (deg)',
    'Mean crossed-arm distance (cm)', 'Crossed-arm distance range (cm)', 'Extra pelvis speed peaks',
  ] : [];
  return <div><SitToStandGraphs {...props} /><FeatureTable {...props} includeUnavailable featureSections={metricOrder.length ? [{ features: metricOrder }] : []} /></div>;
}
