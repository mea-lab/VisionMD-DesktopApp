"""Small process-local queue for GPU-heavy analyses.

One worker deliberately serializes GPU jobs. That keeps Electron/Django request
threads responsive and prevents simultaneous models from exhausting VRAM.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from django.http import JsonResponse
from django.test.client import RequestFactory
from rest_framework.decorators import api_view

from app.views.create_task_views import execute_task

_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="visionmd-analysis")
_JOBS = {}
_LOCK = RLock()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _public(job):
    return {key: deepcopy(value) for key, value in job.items() if key != "future"}


def _run(job_id, task_name, video_id, raw_json, force):
    with _LOCK:
        job = _JOBS[job_id]
        if job["status"] == "cancelled":
            return
        job.update(status="running", progress=None, message="Starting analysis…", startedAt=_now())
    try:
        url = f"/api/{task_name}/?id={video_id}"
        if force:
            url += "&force=1"
        request = RequestFactory().post(url, {"json_data": raw_json})
        def report(progress, message=None):
            with _LOCK:
                job = _JOBS[job_id]
                job["progress"] = max(job.get("progress") or 0, min(99, int(progress)))
                if message:
                    job["message"] = str(message)
        def cancelled():
            with _LOCK:
                return bool(_JOBS[job_id].get("cancelRequested"))
        request.analysis_progress = report
        request.analysis_cancelled = cancelled
        result = execute_task(task_name, request)
        if hasattr(result, "status_code"):
            raise RuntimeError(getattr(result, "data", None) or result.content.decode())
        with _LOCK:
            _JOBS[job_id].update(
                status="completed", progress=100, result=result, completedAt=_now()
            )
    except Exception as exc:
        with _LOCK:
            cancelled = _JOBS[job_id].get("cancelRequested")
            _JOBS[job_id].update(status="cancelled" if cancelled else "failed",
                progress=100, error=None if cancelled else str(exc), completedAt=_now(),
                message="Analysis cancelled" if cancelled else "Analysis failed")


@api_view(["POST"])
def create_analysis_job(request, task_name):
    video_id = request.GET.get("id")
    raw_json = request.POST.get("json_data")
    if not video_id or raw_json is None:
        return JsonResponse({"error": "id and json_data are required"}, status=400)
    job_id = str(uuid4())
    job = {
        "id": job_id,
        "task": task_name,
        "videoId": video_id,
        "status": "queued",
        "progress": 0,
        "createdAt": _now(),
    }
    with _LOCK:
        _JOBS[job_id] = job
        job["future"] = _EXECUTOR.submit(
            _run, job_id, task_name, video_id, raw_json,
            request.GET.get("force") in {"1", "true", "yes"},
        )
    return JsonResponse(_public(job), status=202)


@api_view(["GET", "DELETE"])
def analysis_job(request, job_id):
    with _LOCK:
        job = _JOBS.get(str(job_id))
        if job is None:
            return JsonResponse({"error": "Analysis job not found"}, status=404)
        if request.method == "DELETE":
            if job["status"] == "queued" and job["future"].cancel():
                job.update(status="cancelled", progress=100, completedAt=_now())
            elif job["status"] == "running":
                job["cancelRequested"] = True
                job["message"] = "Cancelling after the current inference batch…"
                return JsonResponse(
                    _public(job),
                    status=202,
                )
        return JsonResponse(_public(job))
