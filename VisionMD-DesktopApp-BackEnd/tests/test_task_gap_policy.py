import numpy as np
import pytest
from app.analysis.tasks.hand_movement_right import HandMovementRightTask
from app.analysis.tasks.base_task import BaseTask
from app.analysis.analysis_quality import assess_analysis_quality

def task():
 t=HandMovementRightTask();t.video_fps=30;return t

def test_scattered_gaps_above_ten_percent_allowed_and_reported():
 frames=[[] if i%4==0 else [[float(i),0.0]] for i in range(60)]
 q=task().check_landmark_gaps(frames)
 assert q['missing_fraction']==.25 and q['needs_review']
 repaired=BaseTask.repair_landmark_track(frames,reject_outliers=False)
 for i,frame in enumerate(frames):
  if frame:assert repaired[i]==frame

def test_sustained_loss_returns_provisional_editable_result():
 frames=[[[0.,0.]]] * 600;frames[40:56]=[[]]*16
 q=task().check_landmark_gaps(frames)
 assert q['long_gap'] and q['needs_review'] and q['provisional']
 repaired=BaseTask.repair_landmark_track(frames,reject_outliers=False)
 assert len(repaired)==len(frames) and np.isfinite(repaired).all()

@pytest.mark.parametrize('frames',[[],[[]]*30,[[[0.,0.]]]+[[]]*5])
def test_empty_or_insufficient_tracking_rejected(frames):
 with pytest.raises(ValueError,match='fewer than two'):task().check_landmark_gaps(frames)

def test_short_consecutive_gap_allowed():
 frames=[[[0.,0.]]] * 60;frames[10:15]=[[]]*5
 assert task().check_landmark_gaps(frames)['longest_missing_run_frames']==5

def test_numpy_tremor_frames_supported():
 frames=[np.zeros((4,2)),[],np.ones((4,2))]
 assert task().check_landmark_gaps(frames)['missing_frame_count']==1

def test_gap_warning_propagates_to_analysis_quality():
 q=task().check_landmark_gaps([[] if i%4==0 else [[float(i),0.]] for i in range(60)])
 report=assess_analysis_quality({'linePlot':{'data':np.sin(np.linspace(0,30,120)).tolist()},'landmarkGapQuality':q})
 assert any('missing' in x.lower() for x in report['reasons'])
