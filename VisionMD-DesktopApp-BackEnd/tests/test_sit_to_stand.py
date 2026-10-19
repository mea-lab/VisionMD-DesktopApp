"""Single-rise measurements and inference-free boundary review contracts."""
import json
import numpy as np
import pytest
from django.urls import resolve
from rest_framework.test import APIRequestFactory
from app.analysis.tasks._sit_to_stand import analyze, FEATURE_LABELS
from app.views.update_sit_to_stand import update_sit_to_stand


@pytest.fixture
def track():
    fps=30.;t=np.arange(121)/fps
    def ease(x):
        x=np.clip(x,0,1);return x**3*(10-15*x+6*x*x)
    q=ease((t-1.25)/1.25);lean=ease((t-.4)/.6)*(1-ease((t-1.5)/1.2))
    p=np.zeros((len(t),17,2),float);p[:,:,0]=320;p[:,:,1]=400
    p[:,14,1]=480-150*q;p[:,[2,5],1]=(p[:,14,1]-140-20*lean)[:,None]
    p[:,2,0]=270;p[:,5,0]=370;p[:,[10,13],1]=700
    p[:,10,0]=285;p[:,13,0]=355;p[:,4]=p[:,5]+[5,30];p[:,7]=p[:,2]+[-5,30]
    return p,fps


def test_single_rise_ten_features_and_frame_timestamps(track):
    p,fps=track;r=analyze(p,fps,2.1)
    assert len(r['sit_to_stand']['features'])==len(FEATURE_LABELS)==10
    assert np.allclose(np.diff(r['linePlot']['time']),1/fps)
    assert r['landmark_start_frame']==63
    assert r['sit_to_stand']['boundaries']['preparation_start']<r['sit_to_stand']['boundaries']['rise_start']
    assert r['sit_to_stand']['features']['extra_speed_peaks']==0
    json.dumps(r,allow_nan=False)


def test_preparation_edit_only_changes_timing(track):
    p,fps=track;r=analyze(p,fps);bounds=dict(r['sit_to_stand']['boundaries']);bounds['preparation_start']+=.1
    edited=analyze(p,fps,boundaries=bounds)
    assert edited['sit_to_stand']['features']['combined_preparation_to_pelvis_end_s']==pytest.approx(r['sit_to_stand']['features']['combined_preparation_to_pelvis_end_s']-.1)
    assert edited['sit_to_stand']['feature_window']==r['sit_to_stand']['feature_window']
    assert edited['landMarks']==r['landMarks']


def test_reviewed_rise_changes_window_but_not_central_time(track):
    p,fps=track;r=analyze(p,fps);bounds=dict(r['sit_to_stand']['boundaries']);bounds['rise_end']-=.1
    edited=analyze(p,fps,boundaries=bounds)
    assert edited['sit_to_stand']['feature_window']['source']=='reviewed_rise_interval'
    assert edited['sit_to_stand']['features']['ascent_time_10_90']==r['sit_to_stand']['features']['ascent_time_10_90']
    assert edited['sit_to_stand']['features']['ascent_speed_cv']!=r['sit_to_stand']['features']['ascent_speed_cv']


@pytest.mark.parametrize('bounds',[
    dict(preparation_start=-1,rise_start=1,rise_end=3),
    dict(preparation_start=2,rise_start=1,rise_end=3),
    dict(preparation_start=0,rise_start=3,rise_end=1),
    dict(preparation_start=0,rise_start=float('nan'),rise_end=3)])
def test_invalid_boundaries_rejected(track,bounds):
    with pytest.raises(ValueError):analyze(*track,boundaries=bounds)


def test_flat_or_missing_track_rejected(track):
    p,fps=track;p[:]=p[0]
    with pytest.raises(ValueError):analyze(p,fps)
    p[:30,14]=np.nan
    with pytest.raises(ValueError):analyze(p,fps)


def test_cached_api_roundtrip_preserves_camera_and_automatic(track):
    r=json.loads(json.dumps(analyze(*track)));r['sit_to_stand']['camera']={'field_of_view':55.5}
    r['sit_to_stand']['subject_height_cm']=175;r['File name']='chair.mp4'
    bounds=dict(r['sit_to_stand']['boundaries']);bounds['preparation_start']+=.1
    factory=APIRequestFactory()
    response=update_sit_to_stand(factory.post('/api/update_sit_to_stand/',{'json_data':json.dumps({'task_data':r,'boundaries':bounds})}))
    assert response.status_code==200
    assert response.data['sit_to_stand']['reviewed'] is True
    assert response.data['sit_to_stand']['camera']=={'field_of_view':55.5}
    assert response.data['analysisQuality']['status']=='review'
    assert not response.data['landmarkSchema']['manualEditing']['supported']
    restored=update_sit_to_stand(factory.post('/api/update_sit_to_stand/',{'json_data':json.dumps({'task_data':response.data,'restore_automatic':True})}))
    assert restored.status_code==200
    assert restored.data['sit_to_stand']['boundaries']==r['sit_to_stand']['automatic_boundaries']
    assert restored.data['sit_to_stand']['features']==r['sit_to_stand']['features']
    assert restored.data['sit_to_stand']['reviewed'] is False


def test_task_and_review_routes():
    assert resolve('/api/sit_to_stand/').url_name=='sit_to_stand'
    assert resolve('/api/update_sit_to_stand/').func is update_sit_to_stand


def test_invalid_cache_is_client_error():
    request=APIRequestFactory().post('/api/update_sit_to_stand/',{'json_data':json.dumps({'task_data':{'sit_to_stand_analysis_cache':{'version':'old'}}})})
    assert update_sit_to_stand(request).status_code==400


def test_initial_task_uses_pose_path_without_gait_phase_inference(track,monkeypatch):
    from app.analysis.tasks.sit_to_stand import SitToStandTask
    p,fps=track
    task=SitToStandTask()
    class Video:
        released=False
        def release(self):self.released=True
    video=Video()
    def prepare(_request):
        task.fps=fps;task.start_frame_idx=30;task.file_name='chair.mp4';task.task_name='Sit To Stand_1';task.height_cm=175;task.video=video
        for key in ('field_of_view','sensor_width','sensor_height','intrinsic_matrix','extrinsic_matrix'):setattr(task,key,None)
    monkeypatch.setattr(task,'prepare_video_parameters',prepare)
    monkeypatch.setattr(task,'get_detector',lambda:object())
    monkeypatch.setattr(task,'extract_landmarks',lambda detector:({'poses2d':p,'poses3d':np.dstack([p,np.zeros(p.shape[:2])])},{}))
    result=task.api_response(object())
    assert isinstance(result,dict)
    assert result['linePlot']['time'][0]==1.
    assert result['sit_to_stand']['subject_height_cm']==175
    assert video.released
    assert result['sit_to_stand']['quality']['metric_scaling']=='not_applied'


def test_missing_pose_gate_blocks_long_gap(track):
    from app.analysis.tasks.sit_to_stand import SitToStandTask
    p,fps=track;task=SitToStandTask();task.fps=fps
    mask=np.zeros(len(p),bool);mask[10:30]=True
    with pytest.raises(ValueError,match='missing body tracking'):task.interpolate_missing_poses(p,mask)


def test_shared_camera_setup_retains_fractional_measurements(tmp_path,settings,monkeypatch):
    from app.analysis.tasks.sit_to_stand import SitToStandTask
    from app.analysis.tasks import gait
    settings.MEDIA_ROOT=str(tmp_path)
    folder=tmp_path/'video_uploads'/'123';folder.mkdir(parents=True)
    (folder/'metadata.json').write_text(json.dumps({'metadata':{'video_name':'chair.mp4','rotation':0}}))
    class Video:
        def get(self,key):return {3:640,4:720,5:30,7:120}.get(key,0)
        def release(self):pass
    monkeypatch.setattr(gait.cv2,'VideoCapture',lambda path:Video())
    payload={'task_name':'Sit To Stand','id':1,'start_time':0,'end_time':1,'height':175,'field_of_view':55.5,'sensor_width':3.45,'sensor_height':3.45,'focal_length':4.25,'boundingBox':{'x':0,'y':0,'width':640,'height':720},'subject_bounding_boxes':[{'frameNumber':i,'data':[]} for i in range(31)]}
    request=APIRequestFactory().post('/api/sit_to_stand/?id=123',{'json_data':json.dumps(payload)})
    task=SitToStandTask();task.prepare_video_parameters(request)
    assert task.field_of_view==55.5
    assert task.intrinsic_matrix[0][0]==pytest.approx(4.25/3.45*1000)
    assert task.intrinsic_matrix[2]==[0,0,1]
