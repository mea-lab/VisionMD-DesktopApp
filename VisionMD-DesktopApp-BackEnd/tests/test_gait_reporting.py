import numpy as np
from app.analysis.signal_analyzers.gait_reporting import public_features
from app.analysis.signal_analyzers.gait_signal_analyzer import GaitSignalAnalyzer


def test_retired_and_exploratory_fields_are_excluded_from_routine_report():
    old = {'Average step length': .7, 'Average velocity': 1.2,
           'SynthGait step length': .7, 'SynthGait step velocity': 1.2,
           'L/R mean legacy step length': .6, 'Step width variability': .03,
           'Step time asymmetry (ms)': 20., 'Torso medial-lateral displacement': .02,
           'Torso medial-lateral RMS velocity (m/s)': .05,
           'Steady-step width SD (m; estimated)': .02,
           'Steady-step width within-segment SD (m; estimated)': .02}
    result = public_features(old)
    assert set(result) == {'Average step length','Average velocity','Steady-step width within-segment SD (m; estimated)'}


def test_length_and_speed_depend_on_ankle_contacts_not_pelvis_translation():
    # Pelvis is stationary (axis defaults to camera depth); ankles progress.
    pose = np.zeros((100,17,3));pose[:,3,0]=-.1;pose[:,6,0]=.1
    times = np.arange(10,90,10)
    left,right=times[1::2],times[::2]
    pose[left,6,2]=left*.01;pose[right,3,2]=right*.01
    out = GaitSignalAnalyzer._synthgait_spatial_features(pose,left,right,30)
    assert np.allclose(out['step_lengths'],.1)
    assert np.allclose(out['step_speeds'],.3)


def test_robust_arm_and_trunk_rom_ignore_isolated_displacement_outlier():
    pose = np.zeros((200,17,3));pose[:,:,2]=np.arange(200)[:,None]*.01
    pose[:,[2,5],1]=-.4;pose[:,[3,6],1]=-.8
    pose[:,3,0]=-.1;pose[:,6,0]=.1
    pose[:,13,2]+=np.linspace(0.,.5,200)
    left,right=np.arange(20,190,20),np.arange(10,180,20)
    first = GaitSignalAnalyzer._synthgait_spatial_features(pose,left,right,30)
    pose[100,13,2]+=100
    pose[100,[0,7,8],0]+=100
    second = GaitSignalAnalyzer._synthgait_spatial_features(pose,left,right,30)
    assert second['left_arm_swing'] < first['left_arm_swing']*1.1
    assert second['torso_ml_range'] < 1.0
