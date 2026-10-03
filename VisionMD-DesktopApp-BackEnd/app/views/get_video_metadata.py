"""Lightweight project-card listing; video validation happens on project open."""
import json
import logging
from pathlib import Path

from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response

logger = logging.getLogger(__name__)
REQUIRED_FIELDS = (
    'id', 'video_name', 'stem_name', 'file_type', 'fps',
    'thumbnail_url', 'video_url', 'rotation', 'last_edited',
)


def read_project_metadata(project_path):
    """Read each metadata file once without decoding video or analysis snapshots."""
    with (project_path / 'metadata.json').open(encoding='utf-8') as handle:
        data = json.load(handle)
    metadata = data.get('metadata')
    if not isinstance(metadata, dict):
        raise ValueError('Project metadata is missing.')
    if any(metadata.get(key) is None or metadata.get(key) == '' for key in REQUIRED_FIELDS):
        raise ValueError('Project metadata is incomplete.')
    # These are cheap file-existence checks. Never open the video decoder here.
    if not (project_path / 'thumbnail.jpg').is_file():
        raise ValueError('Project thumbnail is missing.')
    if not (project_path / metadata['video_name']).is_file():
        raise ValueError('Project video is missing.')
    return data


@api_view(['GET'])
def get_video_metadata(request):
    root = Path(settings.MEDIA_ROOT) / 'video_uploads'
    folder_id = request.GET.get('id')
    if folder_id:
        # Accept a single project folder, not a filesystem path.
        if Path(folder_id).name != folder_id or folder_id in {'.', '..'} or '\\' in folder_id:
            return Response('Invalid project id', status=400)
        project = root / folder_id
        if not project.is_dir():
            return Response('Video project does not exist', status=404)
        try:
            return Response(read_project_metadata(project))
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            logger.warning('Could not read project %s metadata: %s', folder_id, exc)
            return Response('Video project metadata is unavailable', status=404)

    if not root.is_dir():
        return Response([])
    projects = []
    for project in root.iterdir():
        if not project.is_dir():
            continue
        try:
            projects.append(read_project_metadata(project))
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            # A listing request must never delete an unreadable project.
            logger.warning('Skipping project %s metadata: %s', project.name, exc)
    projects.sort(key=lambda data: data['metadata']['last_edited'], reverse=True)
    return Response(projects)
