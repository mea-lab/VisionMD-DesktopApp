"""Review sit-to-stand boundaries using saved image landmarks, without inference."""
import json
from rest_framework.decorators import api_view
from rest_framework.response import Response
from app.analysis.tasks._sit_to_stand import analyze, VERSION
from app.analysis.analysis_quality import assess_analysis_quality
from app.analysis.landmark_schema import attach_landmark_schema


@api_view(['POST'])
def update_sit_to_stand(request):
    try:
        payload = json.loads(request.POST['json_data'])
        if not isinstance(payload,dict) or not isinstance(payload.get('task_data'),dict):
            raise ValueError('A saved sit-to-stand result is required.')
        data = payload['task_data']
        cache = data['sit_to_stand_analysis_cache']
        if not isinstance(cache,dict):
            raise ValueError('A valid landmark cache is required.')
        if cache.get('version') != VERSION:
            raise ValueError('This result requires a fresh sit-to-stand analysis.')
        if payload.get('restore_automatic') is not True and not isinstance(payload.get('boundaries'),dict):
            raise ValueError('Provide all three reviewed boundaries, or restore automatic boundaries.')
        result = analyze(cache['poses2d'],cache['fps'],cache['start_time'],
            boundaries=None if payload.get('restore_automatic') is True else payload['boundaries'],
            automatic=cache['automatic_boundaries'])
        output = {**data,**result}
        # Keep acquisition metadata and the original full recording cache.
        for key in ('camera','subject_height_cm'):
            if key in data.get('sit_to_stand',{}):
                output['sit_to_stand'][key] = data['sit_to_stand'][key]
        for key in ('full_person_visibility','height_scaling'):
            if key in data.get('sit_to_stand',{}).get('quality',{}):
                output['sit_to_stand']['quality'][key] = data['sit_to_stand']['quality'][key]
        output['analysisQuality'] = assess_analysis_quality(output)
        attach_landmark_schema(output,'sit_to_stand')
        return Response(output)
    except (ValueError,KeyError,TypeError,IndexError) as exc:
        return Response({'detail':f'Could not update sit-to-stand boundaries: {exc}'},status=400)
