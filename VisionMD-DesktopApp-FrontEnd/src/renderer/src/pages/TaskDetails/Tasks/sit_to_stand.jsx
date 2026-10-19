import FeatureTable from '../Tables/FeatureTable';
import SitToStandGraphs from '../Graphs/SitToStandGraphs';

export default function SitToStand(props) {
  return <div><SitToStandGraphs {...props} /><FeatureTable {...props} includeUnavailable /></div>;
}
