from django.urls import path
from app.views.get_bounding_boxes import get_bounding_boxes
from app.views.update_plot_data import updatePlotData
from app.views.update_landmarks import update_landmarks
from app.views.create_task_views import generate_task_urlpatterns
from app.views.upload_video import upload_video
from app.views.get_video_data import get_video_data
from app.views.get_video_metadata import get_video_metadata
from app.views.update_video_data import update_video_data
from app.views.delete_video import delete_video
from app.views.new_path import new_path
from app.views.import_project_snapshot import import_project_snapshot
from app.views.update_gait_segments import update_gait_segments
from app.views.analysis_jobs import create_analysis_job, analysis_job

urlpatterns = [
    # GET Requests
    path('get_bounding_boxes/', get_bounding_boxes),
    path('get_video_data/', get_video_data),
    path('get_video_metadata/', get_video_metadata),

    # PUT Request
    path('update_plot/', updatePlotData),
    path('update_landmarks/', update_landmarks),
    path('update_gait_segments/', update_gait_segments),
    path('update_video_data/', update_video_data),

    # POST Requests
    path('upload_video/', upload_video),
    path('import_project_snapshot/', import_project_snapshot),
    path('analysis_jobs/<str:task_name>/', create_analysis_job),
    path('analysis_jobs/status/<uuid:job_id>/', analysis_job),

    # DELETE Requests
    path('delete_video/', delete_video),
]

urlpatterns += generate_task_urlpatterns()
