"""Single frontal sit-to-stand, sharing gait's video/camera/MeTRAbs input path."""
import json
import numpy as np
from rest_framework.response import Response
from .gait import GaitTask
from ._sit_to_stand import analyze, runs


class SitToStandTask(GaitTask):
    """BaseTask implementation via the existing full-frame gait pose extractor.

    Only pose estimation is shared; gait phases/transformer and gait feature
    estimation are never called. Project source videos are never deleted.
    """

    def __init__(self):
        super().__init__()
        self.video = None
        self.task_norm_strategy = 'SHOULDER_ANKLE_REFERENCE'
        self.tracking_quality = {}

    def prepare_video_parameters(self, request):
        # Validate camera inputs before the shared video setup uses them.
        payload = json.loads(request.POST['json_data'])
        for key in ('field_of_view', 'sensor_width', 'sensor_height', 'focal_length'):
            value = payload.get(key)
            value = None if value in (None, '') else float(value)
            if value is not None and (not np.isfinite(value) or value <= 0):
                raise ValueError('Camera measurements must be positive finite numbers.')
        fov = payload.get('field_of_view')
        if fov not in (None, '') and float(fov) >= 180:
            raise ValueError('Field of view must be between 0 and 180 degrees.')
        parameters = super().prepare_video_parameters(request)
        return parameters

    def interpolate_missing_poses(self, poses, missing_mask):
        missing = np.asarray(missing_mask,bool) | ~np.isfinite(poses).all(axis=(1,2))
        longest = max((b-a for a,b in runs(missing)),default=0)/self.fps
        if missing.mean() > .10 or longest > .5:
            raise ValueError('Too much missing body tracking. Expand the subject box and select a fully visible rise.')
        if poses.shape[-1] == 2:
            self.tracking_quality = {'missing_fraction':float(missing.mean()),'longest_missing_run_seconds':float(longest),'needs_review':bool(missing.any())}
        return super().interpolate_missing_poses(poses,missing)

    def get_signal_analyzer(self):
        return analyze

    def calculate_signal(self, essential_landmarks):
        p = np.asarray(essential_landmarks,float)
        return (p[:,[10,13],1].mean(axis=1)-p[:,14,1]).tolist()

    def calculate_normalization_factor(self, essential_landmarks):
        result = analyze(essential_landmarks,self.fps)
        return result['normalization_factor']

    def api_response(self, request):
        try:
            self.prepare_video_parameters(request)
            self._progress(3,'Loading the body pose model…')
            self._check_cancelled()
            detector = self.get_detector()
            # Adapt gait progress wording, while keeping its cancellation/device fallback.
            progress = self._progress
            self._progress = lambda value,message=None: progress(value,message.replace('gait','sit-to-stand') if message else None)
            original, _mirrored = self.extract_landmarks(detector)
            self._check_cancelled()
            self._progress(90,'Measuring the sit-to-stand transition…')
            # Frame-aligned time origin, including non-integral task start times.
            result = analyze(original['poses2d'],self.fps,self.start_frame_idx/self.fps)
            result.update({'File name':self.file_name,'Task name':self.task_name,'landMarks_3D':original['poses3d'].tolist(),'landmarkGapQuality':self.tracking_quality})
            result['sit_to_stand']['camera'] = {key:getattr(self,key) for key in ('field_of_view','sensor_width','sensor_height','focal_length','intrinsic_matrix','extrinsic_matrix')}
            result['sit_to_stand']['subject_height_cm'] = self.height_cm
            result['sit_to_stand']['quality']['full_person_visibility'] = self.full_person_visibility or 'not_certified'
            result['sit_to_stand']['quality']['height_scaling'] = 'Not applied: no validated upright full-person height reference.'
            return result
        except (ValueError,KeyError,TypeError) as exc:
            return Response({'detail':str(exc)},status=400)
        except Exception as exc:
            return Response({'detail':f'Sit-to-stand analysis failed: {exc}'},status=500)
        finally:
            if self.video is not None:
                self.video.release()
