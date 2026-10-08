"""VisionMD pronation/supination using the validated YOLO -> WiLoR pipeline.

Pipeline ownership is deliberately separated:

* this task adapts VisionMD requests, cached landmarks, and visualization;
* ``_wilor_ps_pipeline`` owns hand-track association, WiLoR batching,
  sequence-level 3-D branch selection, angle repairs, and filtering.

The selected VisionMD subject box is always applied before YOLO hand
localization, preventing bystanders and reflections from competing with the
task subject. A compact fixed hand ROI is attempted when appropriate. Wide
hand trajectories start in dynamic mode; a diagnostically failed fixed result
is automatically rerun with interpolated dynamic ROIs.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
import cv2, numpy as np, torch
from django.conf import settings
from rest_framework.response import Response
from ultralytics import YOLO
from .base_task import BaseTask
from ._wilor_ps_pipeline import (WiLorBatch, angle_anomaly_diagnostics,
    choose_angle_estimator, geometry_angle, landmark_temporal_decode,
    palm_normal_angle, repair_short_flip_intervals,
    repair_uncertain_angle_samples, select_moving_track_timed, square_roi,
    zero_phase_lowpass)
from ._wilor_temporal_refiner import refine_failed_trajectory
from ._mediapipe_ps_screen import screen_mediapipe_world_landmarks
from app.analysis.model_registry import reset_yolo_runtime
from app.analysis.signal_analyzers.peakfinder_signal_analyzer import PeakfinderSignalAnalyzer
from app.analysis.torch_device import preferred_device, run_with_device_fallback

_HAND_MODEL = None
_HAND_DEVICE = None
_WILOR_MODEL = None

def _device():
    return preferred_device()

def _hand_model_path():
    configured=os.environ.get("VISIONMD_HAND_DETECTOR_MODEL")
    paths=[configured] if configured else []
    paths += [str(Path(settings.BASE_DIR)/"app/analysis/models/hand_detector/best_hand_model.pt"),
              "/home/apkuser/Documents/Models/HandDetectorYOLO/best_hand_model.pt"]
    for path in paths:
        if path and Path(path).is_file(): return path
    raise FileNotFoundError("Set VISIONMD_HAND_DETECTOR_MODEL to best_hand_model.pt")

def _models():
    global _HAND_MODEL,_HAND_DEVICE,_WILOR_MODEL
    if _HAND_MODEL is None:
        _HAND_MODEL = YOLO(_hand_model_path())
        _HAND_DEVICE = _device()
    if _WILOR_MODEL is None:
        model_dir = os.environ.get("VISIONMD_WILOR_MODEL_DIR")
        if not model_dir:
            model_dir = str(Path(settings.BASE_DIR) / "app/analysis/models/wilor_mini")
        _WILOR_MODEL,_actual_device = run_with_device_fallback(
            lambda active_device: WiLorBatch(active_device, model_dir),
            _device(),
            label="WiLoR model initialization",
        )
        _HAND_DEVICE = preferred_device()
    return _HAND_MODEL, _WILOR_MODEL

def _square(box,width,height,scale=1.5):
    box=np.asarray(box,float); center=(box[:2]+box[2:])/2; side=max(box[2]-box[0],box[3]-box[1])*scale
    return np.array([max(0,center[0]-side/2),max(0,center[1]-side/2),
                     min(width-1,center[0]+side/2),min(height-1,center[1]+side/2)])

def _process(raw,fps,right):
    """Exact post-processing order used by the validated standalone runner."""
    corrected,diag=landmark_temporal_decode(raw)
    raw_angle=geometry_angle(raw,resolve_normals=False)
    selected=np.degrees(np.unwrap(np.radians(geometry_angle(corrected,resolve_normals=False))))
    palm=np.degrees(np.unwrap(np.radians(palm_normal_angle(raw,right))))
    geometry=np.degrees(np.unwrap(np.radians(raw_angle)))
    chosen,method,geometry_score,palm_score=choose_angle_estimator(selected,palm,geometry)
    repaired,flip=repair_short_flip_intervals(chosen,max_interval_frames=round(fps*.6))
    anomaly,low=angle_anomaly_diagnostics(repaired,diag["landmark_quality_score"],fps)
    evidence=low & (diag["landmark_quality_score"]<.05)
    uncertain,replaced=repair_uncertain_angle_samples(repaired,evidence,fps)
    final,cutoff=zero_phase_lowpass(uncertain,fps,10.)
    steps=np.abs(np.diff(final)); robust=float(np.percentile(final,95)-np.percentile(final,5))
    quality={"low_confidence_fraction":float(low.mean()),
             "max_landmark_step":float(np.nanmax(diag["landmark_step_raw"])),
             "p99_angle_step_deg":float(np.percentile(steps,99)) if len(steps) else 0.,
             "robust_range_deg":robust,"angle_method":method,
             "geometry_score":float(geometry_score),"palm_score":float(palm_score),
             "branch_frames":int(np.sum(diag["branch_flipped"])),
             "flip_repaired_frames":int(np.sum(flip)),"uncertain_replaced":int(np.sum(replaced)),
             "lowpass_cutoff_hz":float(cutoff)}
    quality["pass"]=(quality["low_confidence_fraction"]<=.10 and quality["max_landmark_step"]<=.50
                     and quality["p99_angle_step_deg"]<=60 and robust<=320)
    return final,corrected,diag,quality

class HandPronationSupinationTask(BaseTask):
    """Shared implementation; concrete subclasses select left or right hand."""

    LANDMARKS = {"WRIST": 0, "INDEX_MCP": 5, "MIDDLE_MCP": 9, "PINKY_MCP": 17}
    HAND_LABEL=None
    def __init__(self):
        self.video_id=self.video_fps=self.video_rotation=None; self.video_file_path=self.video_file_name=None
        self.task_name=self.task_norm_strategy=None; self.task_start_time=self.task_end_time=None
        self.task_start_frame_idx=self.task_end_frame_idx=None; self.original_bounding_box=None
        self.enlarged_bounding_box=self.subject_bounding_boxes=None; self._angles=None; self._pipeline={}
        self.ps_method="auto"
        self._progress=lambda *_args,**_kwargs:None; self._cancelled=lambda:False

    def api_response(self,request):
        try:
            self.prepare_video_parameters(request); essential,all_landmarks=self.extract_landmarks()
            all_landmarks=self.interpolate_missing_landmarks(all_landmarks)
            result=self.get_signal_analyzer().analyze(self.calculate_signal(essential),1.,self.task_start_time,self.task_end_time)
            return {"File name":self.video_file_name,"Task name":self.task_name,**result,
                    "landMarks":essential,"allLandMarks":all_landmarks,"normalization_factor":1.,
                    "landmark_start_frame":self.task_start_frame_idx,
                    "landmark_fps":self.video_fps,
                    "psPipeline":self._pipeline}
        except Exception as exc: return Response(str(exc),status=500)

    def prepare_video_parameters(self,request):
        self._progress=getattr(request,"analysis_progress",self._progress)
        self._cancelled=getattr(request,"analysis_cancelled",self._cancelled)
        self._progress(3,"Preparing P/S analysis")
        self.video_id=request.GET.get("id"); payload=json.loads(request.POST["json_data"])
        folder=os.path.join(settings.MEDIA_ROOT,"video_uploads",self.video_id)
        with open(os.path.join(folder,"metadata.json"),encoding="utf-8") as h: meta=json.load(h)["metadata"]
        self.video_fps=float(meta["fps"]); self.video_rotation=meta["rotation"]; self.video_file_name=meta["video_name"]
        self.video_file_path=os.path.join(folder,self.video_file_name); self.task_name=payload["task_name"]
        self.task_norm_strategy=payload.get("norm_strategy","NONE"); self.task_start_time=float(payload["start_time"]); self.task_end_time=float(payload["end_time"])
        self.ps_method=payload.get("ps_method","auto")
        self.task_start_frame_idx=round(self.video_fps*self.task_start_time); self.task_end_frame_idx=round(self.video_fps*self.task_end_time); self.original_bounding_box=payload["boundingBox"]

    def get_signal_analyzer(self): return PeakfinderSignalAnalyzer()

    def get_detector(self):
        """Return the shared WiLoR wrapper required by the BaseTask contract."""
        return _models()[1]

    def _localize(self,model):
        global _HAND_DEVICE
        if _HAND_DEVICE is None:
            _HAND_DEVICE = _device()
        b=self.original_bounding_box; px1,py1=int(b["x"]),int(b["y"]); px2,py2=px1+int(b["width"]),py1+int(b["height"])
        cap=cv2.VideoCapture(self.video_file_path); cap.set(cv2.CAP_PROP_POS_FRAMES,self.task_start_frame_idx)
        count=self.task_end_frame_idx-self.task_start_frame_idx; step=max(1,round(self.video_fps/12.)); samples={}; cls=1 if self.HAND_LABEL=="Right" else 0
        width = height = None
        for i in range(count):
            if self._cancelled(): raise RuntimeError("Analysis cancelled")
            ok,frame=cap.read()
            if not ok: break
            if i%step: continue
            frame=BaseTask.correct_frame_orientation(frame,self.video_rotation)
            if width is None:
                height, width = frame.shape[:2]
                px1, px2 = np.clip([px1, px2], 0, width).astype(int)
                py1, py2 = np.clip([py1, py2], 0, height).astype(int)
                if px2 <= px1 or py2 <= py1:
                    raise ValueError("The selected subject bounding box is outside the video frame.")
            crop=frame[py1:py2,px1:px2]
            def predict(active_device):
                return model.predict(crop,device=active_device,conf=.05,
                                     classes=[cls],verbose=False)[0]
            result,_HAND_DEVICE=run_with_device_fallback(
                predict,_HAND_DEVICE,label="YOLO hand localization",
                on_cpu_fallback=lambda: reset_yolo_runtime(model))
            if result.boxes is not None and len(result.boxes):
                boxes=result.boxes.xyxy.cpu().numpy().astype(float); boxes[:,[0,2]]+=px1; boxes[:,[1,3]]+=py1; samples[i]=list(boxes)
            if i%max(1,count//20)==0: self._progress(32+16*i/max(1,count),"YOLO hand localization")
        cap.release()
        track=select_moving_track_timed(samples)
        timed=np.array([i for i,_ in track]); boxes=np.array([x for _,x in track]); ids=np.arange(count)
        interpolated=np.column_stack([np.interp(ids,timed,boxes[:,j]) for j in range(4)])
        fixed=square_roi(list(boxes),width,height,1.5); median=float(np.median(np.max(boxes[:,2:]-boxes[:,:2],axis=1)))
        ratio=float(max(fixed[2]-fixed[0],fixed[3]-fixed[1])/max(median*1.5,1)); dynamic=np.array([_square(x,width,height) for x in interpolated])
        return fixed,dynamic,ratio,count,len(track)/max(1,int(np.ceil(count/step)))

    def _infer(self,wilor,rois,count):
        cap=cv2.VideoCapture(self.video_file_path); cap.set(cv2.CAP_PROP_POS_FRAMES,self.task_start_frame_idx); raw=[]; projected=[]; pending=[]; start=0
        def flush():
            nonlocal pending,start
            if not pending:return
            if self._cancelled(): raise RuntimeError("Analysis cancelled")
            indices=range(start,start+len(pending)); a,b=wilor.infer_rois_with_projection(pending,[rois[i] for i in indices],self.HAND_LABEL=="Right"); raw.append(a); projected.append(b); start+=len(pending); pending=[]
            self._progress(55+25*start/max(1,count),"WiLoR 3-D hand pose inference")
        for _ in range(count):
            if self._cancelled(): raise RuntimeError("Analysis cancelled")
            ok,frame=cap.read()
            if not ok:break
            pending.append(BaseTask.correct_frame_orientation(frame,self.video_rotation))
            if len(pending)>=32:flush()
        flush(); cap.release()
        if not raw:
            raise ValueError("No video frames could be read for the selected task interval.")
        return np.concatenate(raw),np.concatenate(projected)

    def extract_landmarks(self):
        total_started=time.perf_counter(); screening=None
        if self.ps_method != "wilor":
            self._progress(5,"Trying fast MediaPipe 3-D hand tracking")
            screening_started=time.perf_counter()
            screening=screen_mediapipe_world_landmarks(
                self.video_file_path,self.video_rotation,self.task_start_frame_idx,
                self.task_end_frame_idx,self.video_fps,self.original_bounding_box,
                self.HAND_LABEL=="Right",
                lambda raw:_process(raw,self.video_fps,self.HAND_LABEL=="Right"),
                progress=lambda fraction:self._progress(5+25*fraction,"Trying fast MediaPipe 3-D hand tracking"),
                cancelled=self._cancelled)
            screening["seconds"]=round(time.perf_counter()-screening_started,3)
            if screening["accepted"]:
                self._progress(96,"MediaPipe passed screening; finalizing provisional result")
                final=screening["final"]; initial=float(np.median(final[:max(1,round(.5*self.video_fps))]))
                self._angles=(final-initial).tolist()
                self._pipeline={"version":"mediapipe-screen-wilor-fallback-v1",
                    "engine":"mediapipe_world_landmarks","requires_verification":True,
                    "screening":{key:value for key,value in screening.items()
                                 if key not in {"raw","projected","corrected","final","diagnostics"}},
                    "quality":screening["quality"],
                    "timing":{"total_seconds":round(time.perf_counter()-total_started,3),
                              "mediapipe_screen_seconds":screening["seconds"]}}
                return self._format_output(screening["corrected"],screening["projected"])

            reason="; ".join(screening.get("reasons") or ["quality gate failed"])
            self._progress(31,f"MediaPipe was not reliable ({reason}). Switching to YOLO + WiLoR")

        if self._cancelled(): raise RuntimeError("Analysis cancelled")
        self._progress(32,"Loading YOLO + WiLoR models")
        localization_started=time.perf_counter(); hand,wilor=_models(); fixed,dynamic,ratio,count,coverage=self._localize(hand); localization_seconds=time.perf_counter()-localization_started; direct_dynamic=ratio>1.7
        inference_started=time.perf_counter()
        rois=dynamic if direct_dynamic else np.repeat(fixed[None,:],count,axis=0); raw,projected=self._infer(wilor,rois,count)
        initial_inference_seconds=time.perf_counter()-inference_started
        self._progress(82,"Checking landmark continuity and angle quality")
        final,corrected,diag,quality=_process(raw,self.video_fps,self.HAND_LABEL=="Right"); rerun=not direct_dynamic and not quality["pass"]
        rerun_seconds=0.
        if rerun:
            self._progress(84,"Fixed ROI failed quality checks; retrying with dynamic ROIs")
            rerun_started=time.perf_counter(); rois=dynamic; raw,projected=self._infer(wilor,rois,count); final,corrected,diag,quality=_process(raw,self.video_fps,self.HAND_LABEL=="Right"); rerun_seconds=time.perf_counter()-rerun_started
        initial=float(np.median(final[:max(1,round(.5*self.video_fps))]))
        relative=final-initial
        temporal={"attempted":False,"accepted":False,
                  "reason":"deterministic_trajectory_passed"}
        if not quality["pass"]:
            try:
                relative,temporal=refine_failed_trajectory(
                    raw,rois[:len(raw)],final,self.HAND_LABEL=="Right",self.video_fps)
            except Exception as exc:
                # WiLoR output remains usable when an optional temporal model
                # is absent or unavailable on a deployment.
                temporal={"attempted":True,"accepted":False,
                          "rejection_reasons":["refiner_error"],
                          "error":f"{type(exc).__name__}: {exc}"}
        self._angles=relative.tolist()
        self._progress(98,"Finalizing P/S signal")
        self._pipeline={"version":"mediapipe-screen-wilor-fallback-v1","engine":"yolo_wilor","requires_verification":not quality["pass"],"roi_mode":"dynamic" if direct_dynamic or rerun else "fixed","dynamic_rerun":rerun,"fixed_to_typical_crop_ratio":ratio,"localization_fps":12.,"track_coverage":coverage,"quality":quality,"temporal_refiner":temporal,"hand_detector":_hand_model_path(),"screening":{key:value for key,value in screening.items() if key not in {"raw","projected","corrected","final","diagnostics"}} if screening else {"skipped":True,"reason":"WiLoR explicitly requested"},"timing":{"localization_seconds":round(localization_seconds,3),"initial_wilor_seconds":round(initial_inference_seconds,3),"dynamic_rerun_seconds":round(rerun_seconds,3),"total_seconds":round(time.perf_counter()-total_started,3)}}
        return self._format_output(corrected,projected)

    def _format_output(self,corrected,projected):
        """Serialize full-frame 2-D overlays plus cached 3-D/final-angle data."""
        essential=[]; all_points=[]
        for angle,world,xy in zip(self._angles,corrected,projected):
            # ``infer_rois_with_projection`` returns coordinates in the full,
            # oriented video frame. VisionMD's SVG and canvas overlays use the
            # same absolute coordinate system; subtracting the selected task
            # box origin would shift every point up and left on screen.
            display=xy
            # The sixth value stores the fully post-processed angle. VisionMD
            # later recalculates subranges from cached landmarks; persisting
            # it here guarantees that operation uses this exact pipeline.
            essential.append([[float(display[i,0]),float(display[i,1]),
                               *map(float,world[i]),float(angle)]
                              for i in (0,5,9,17)])
            all_points.append([[float(x),float(y),0.] for x,y in display])
        return essential,all_points

    def calculate_signal(self,essential):
        cached = [frame[0][5] for frame in essential
                  if frame and frame[0] and len(frame[0]) > 5]
        if len(cached) == len(essential):
            return [float(value) for value in cached]
        if self._angles is not None and len(self._angles) == len(essential):
            return self._angles
        raise ValueError(
            "Cached P/S landmarks predate adaptive-yolo-wilor-v1; rerun analysis "
            "once to store the finalized angle signal."
        )
    def calculate_normalization_factor(self,landmarks): return 1.
