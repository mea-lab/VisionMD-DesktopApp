import numpy as np
import pytest
from app.analysis.signal_analyzers import peakfinder_signal_analyzer as module
from app.analysis.analysis_quality import assess_analysis_quality

@pytest.mark.parametrize('message',[
 'zero-size array to reduction operation maximum which has no identity',
 'No complete movement cycles were found.',
 'Movement cycle has an empty opening or closing interval.',
])
def test_cycle_failure_keeps_editable_waveform_without_fabricated_measures(monkeypatch,message):
 def fail(_):raise ValueError(message)
 monkeypatch.setattr(module,'get_output',fail)
 out=module.PeakfinderSignalAnalyzer().analyze([0.,1.,0.,1.,0.],2.,0.,1.)
 assert out['radarTable'] is None
 assert out['featureEstimationQuality']['status']=='needs_correction'
 assert len(out['linePlot']['data'])==60
 assert np.isfinite(out['velocityPlot']['data']).all()
 assert out['peaks']=={'time':[],'data':[]}
 assert any('could not be calculated' in r for r in assess_analysis_quality(out)['reasons'])

def test_unrelated_errors_remain_errors(monkeypatch):
 def fail(_):raise ValueError('unrelated bug')
 monkeypatch.setattr(module,'get_output',fail)
 with pytest.raises(ValueError,match='unrelated bug'):
  module.PeakfinderSignalAnalyzer().analyze([0.,1.,0.],1.,0.,1.)

def test_no_cycles_is_explicit_before_feature_computation(monkeypatch):
 monkeypatch.setattr(module,'normalized_peakFinder',lambda *a,**k:(np.arange(10.),np.ones(10),[],[],[]))
 out=module.PeakfinderSignalAnalyzer().analyze([0.,1.,0.],1.,0.,1.)
 assert out['featureEstimationQuality']['status']=='needs_correction'
 assert out['radarTable'] is None
