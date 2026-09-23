#!/usr/bin/env python3
"""Batch-run VisionMD task models for stable, detected person candidates.

The per-candidate result JSON is produced by the same task class used by the
desktop app and can therefore be imported in its Task Details view.
"""
import argparse
import importlib
import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

# The script is intentionally runnable by path from any working directory.
# Bootstrap Django before importing VisionMD modules or DRF response classes.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "VideoAnalysisToolBackend.settings")
import django
django.setup()

import cv2
import numpy as np
from django.conf import settings
from django.test import RequestFactory
from rest_framework.response import Response
from ultralytics import YOLO
from app.analysis.analysis_quality import assess_analysis_quality

TASKS = {
    "finger_tap_left": "Finger Tap Left",
    "finger_tap_right": "Finger Tap Right",
    "gait": "Gait",
    "hand_movement_left": "Hand Movement Left",
    "hand_movement_right": "Hand Movement Right",
    "hand_pronation_left": "Hand Pronation Left",
    "hand_pronation_right": "Hand Pronation Right",
    "hand_tremor_left_elbow_extended": "Hand Tremor Left Elbow Extended",
    "hand_tremor_right_elbow_extended": "Hand Tremor Right Elbow Extended",
    "leg_agility_left": "Leg agility Left",
    "leg_agility_right": "Leg agility Right",
    "toe_tapping_left": "Toe tapping Left",
    "toe_tapping_right": "Toe tapping Right",
}
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}
DEFAULT_NORM_STRATEGY = {
    "hand_movement_left": "PALMSIZE",
    "hand_movement_right": "PALMSIZE",
}

def iou(a, b):
    ax1, ay1, ax2, ay2 = a["box"]; bx1, by1, bx2, by2 = b["box"]
    inter = max(0, min(ax2,bx2)-max(ax1,bx1))*max(0, min(ay2,by2)-max(ay1,by1))
    union = (ax2-ax1)*(ay2-ay1)+(bx2-bx1)*(by2-by1)-inter
    return inter/union if union else 0

def centre_distance(a, b, diagonal):
    ac=np.array([(a["box"][0]+a["box"][2])/2,(a["box"][1]+a["box"][3])/2])
    bc=np.array([(b["box"][0]+b["box"][2])/2,(b["box"][1]+b["box"][3])/2])
    return float(np.linalg.norm(ac-bc)/diagonal)

def pose_distance(a, b, diagonal):
    ka,kb=a.get("keypoints"),b.get("keypoints")
    if ka is None or kb is None: return 1.
    valid=(ka[:,2]>.25)&(kb[:,2]>.25)
    return float(np.linalg.norm(ka[valid,:2]-kb[valid,:2],axis=1).mean()/diagonal) if valid.sum()>=3 else 1.

def static_box(observations, width, height, padding):
    boxes=np.asarray([x["box"] for x in observations],dtype=float)
    x1,y1=np.quantile(boxes[:,:2],.05,axis=0); x2,y2=np.quantile(boxes[:,2:],.95,axis=0); bw,bh=x2-x1,y2-y1
    return [int(round(x)) for x in (max(0,x1-padding*bw),max(0,y1-padding*bh),min(width,x2+padding*bw),min(height,y2+padding*bh))]

def discover(video, model, sample_fps, device, imgsz, conf, min_coverage, padding):
    """Static-ROI association method from discover_person_candidates.py."""
    cap=cv2.VideoCapture(str(video))
    if not cap.isOpened(): raise FileNotFoundError(video)
    fps=cap.get(cv2.CAP_PROP_FPS) or 30.; width,height=int(cap.get(3)),int(cap.get(4)); count=int(cap.get(7))
    step=max(1,round(fps/sample_fps)); diagonal=float(np.hypot(width,height)); tracks=[]; frame=sample=0
    while True:
        ok,image=cap.read()
        if not ok: break
        if frame % step: frame+=1; continue
        result=model.predict(image,classes=[0],conf=conf,imgsz=imgsz,device=device,verbose=False)[0]
        boxes=result.boxes.xyxy.cpu().numpy() if result.boxes else np.empty((0,4)); scores=result.boxes.conf.cpu().numpy() if result.boxes else []
        keypoints=result.keypoints.data.cpu().numpy() if result.keypoints is not None else []
        detections=[{"box":box.tolist(),"confidence":float(scores[i]),"keypoints":keypoints[i] if len(keypoints) else None,"sample":sample} for i,box in enumerate(boxes)]
        pairs=[]
        for ti,track in enumerate(tracks):
            prior=track["observations"][-1]
            if sample-prior["sample"]<=3:
                for di,det in enumerate(detections):
                    overlap,distance=iou(prior,det),centre_distance(prior,det,diagonal); pose=pose_distance(prior,det,diagonal)
                    if overlap>=.03 or distance<.16: pairs.append((.55*overlap+.25*max(0,1-3*distance)+.20*max(0,1-3*pose),ti,di))
        used_t,used_d=set(),set()
        for score,ti,di in sorted(pairs,reverse=True):
            if score>=.22 and ti not in used_t and di not in used_d:
                tracks[ti]["observations"].append(detections[di]); used_t.add(ti); used_d.add(di)
        for di,det in enumerate(detections):
            if di not in used_d: tracks.append({"observations":[det]})
        sample+=1; frame+=1
    cap.release(); candidates=[]
    for n,track in enumerate(tracks,1):
        coverage=len(track["observations"])/max(1,sample)
        if coverage>=min_coverage: candidates.append({"candidate_id":f"candidate_{n:03d}","bbox_xyxy":static_box(track["observations"],width,height,padding),"coverage":round(coverage,4),"mean_confidence":round(float(np.mean([x["confidence"] for x in track["observations"]])),4)})
    return {"fps":fps,"width":width,"height":height,"frame_count":count,"candidates":candidates}

def task_class(key):
    module=importlib.import_module(f"app.analysis.tasks.{key}")
    return getattr(module,"".join(x.capitalize() for x in key.split("_"))+"Task")

def stage(video, info, root):
    folder=root/"video_uploads"/uuid.uuid4().hex; folder.mkdir(parents=True); target=folder/video.name
    try: os.symlink(video.resolve(),target)
    except OSError: shutil.copy2(video,target)
    (folder/"metadata.json").write_text(json.dumps({"metadata":{"fps":info["fps"],"rotation":0,"video_name":video.name}}))
    return folder.name

def analyze(video, info, candidate, key, height_cm, norm_strategy, root):
    video_id=stage(video,info,root); x1,y1,x2,y2=candidate["bbox_xyxy"]; duration=info["frame_count"]/info["fps"]
    data={"boundingBox":{"x":x1,"y":y1,"width":x2-x1,"height":y2-y1},"task_name":TASKS[key],"start_time":0.,"end_time":duration,"norm_strategy":norm_strategy}
    if key=="gait":
        if height_cm is None: raise ValueError("--height-cm is required for gait")
        data.update({"id":candidate["candidate_id"],"height":height_cm,"subject_bounding_boxes":[{"frameNumber":i,"data":[{"id":candidate["candidate_id"],"x":x1,"y":y1,"width":x2-x1,"height":y2-y1,"Subject":True}]} for i in range(info["frame_count"])]})
    request=RequestFactory().post("/",{"json_data":json.dumps(data)}); request.GET=request.GET.copy(); request.GET["id"]=video_id
    result=task_class(key)().api_response(request)
    if isinstance(result,Response): raise RuntimeError(result.data)
    return result

def quality(result):
    radar=result.get("radarTable",{}); candidates=[]
    line=result.get("linePlot",{})
    if isinstance(line,dict): candidates.append(line.get("data",[]))
    signals=result.get("signals",{})
    if isinstance(signals,dict): candidates.extend(signals.values())
    numeric=[]
    for values in candidates:
        try:
            array=np.asarray(values,dtype=float).reshape(-1)
        except (TypeError,ValueError):
            continue
        if array.size: numeric.append(array)
    signal=max(numeric,key=lambda value:value.size,default=np.empty(0,dtype=float))
    amplitude=float(np.ptp(signal)) if signal.size else 0.; frequency=float(radar.get("Frequency",0)); peaks=len(result.get("peaks",{}).get("data",[]))
    # A flat non-gait trace is not a movement candidate.  Gait has a different
    # result schema and is left to its own task pipeline to validate.
    if signal.size and amplitude <= 1e-8:
        raise ValueError("discarded: no measurable movement in the analyzed signal")
    return round(100*min(1,amplitude)+20*min(peaks,6)+10*min(frequency,5),3),{"signal_amplitude":amplitude,"frequency_hz":frequency,"peaks":peaks}

def project_snapshot(video, info, candidate, key, norm_strategy, result):
    """Build a complete document accepted by Home -> Load Project JSON."""
    x1,y1,x2,y2=candidate["bbox_xyxy"]; duration=info["frame_count"]/info["fps"]
    person_id=1
    box={"id":person_id,"x":x1,"y":y1,"width":x2-x1,"height":y2-y1,"Subject":True}
    bounding_boxes=[{"frameNumber":frame,"data":[dict(box)]} for frame in range(info["frame_count"])]
    persons=[{"id":person_id,"name":"Person 1","frameNumber":0,"timestamp":"0.00","isSubject":True}]
    task={"id":1,"name":TASKS[key],"start":0.0,"end":duration,
          "x":x1,"y":y1,"box_width":x2-x1,"box_height":y2-y1,
          "norm_strategy":norm_strategy,"full_video":True,"data":result}
    return {"format":"visionmd-project","version":1,
            "video":{"name":video.name,"fps":info["fps"]},
            "data":{"fps":info["fps"],"persons":persons,
                    "boundingBoxes":bounding_boxes,"tasks":[task]}}

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("source",type=Path); parser.add_argument("--task",choices=TASKS,required=True); parser.add_argument("--weights",type=Path,required=True); parser.add_argument("--output-dir",type=Path,required=True); parser.add_argument("--height-cm",type=float); parser.add_argument("--norm-strategy",help="Override the task default normalization"); parser.add_argument("--sample-fps",type=float,default=2.); parser.add_argument("--device",default="cuda"); parser.add_argument("--imgsz",type=int,default=960); parser.add_argument("--conf",type=float,default=.25); parser.add_argument("--min-coverage",type=float,default=.20); parser.add_argument("--padding",type=float,default=.12)
    args=parser.parse_args(); videos=[args.source] if args.source.is_file() else sorted(p for p in args.source.iterdir() if p.suffix.lower() in VIDEO_SUFFIXES)
    if not videos: parser.error("No supported videos found");
    if args.sample_fps<=0: parser.error("--sample-fps must be positive")
    args.output_dir.mkdir(parents=True,exist_ok=True); model=YOLO(str(args.weights)); original_root=settings.MEDIA_ROOT
    norm_strategy=args.norm_strategy or DEFAULT_NORM_STRATEGY.get(args.task,"INDEXSIZE")
    with tempfile.TemporaryDirectory(prefix="visionmd-batch-") as temporary:
        settings.MEDIA_ROOT=temporary
        try:
            for video in videos:
                info=discover(video,model,args.sample_fps,args.device,args.imgsz,args.conf,args.min_coverage,args.padding); entries=[]
                for candidate in info["candidates"]:
                    entry=dict(candidate)
                    try:
                        result=analyze(video,info,candidate,args.task,args.height_cm,norm_strategy,Path(temporary))
                        result["analysisQuality"]=assess_analysis_quality(result)
                        score,metrics=quality(result)
                        output=args.output_dir/f"{video.stem}_{candidate['candidate_id']}_{args.task}.json"
                        output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
                        project_output=args.output_dir/f"{video.stem}_{candidate['candidate_id']}_{args.task}_visionmd_project.json"
                        snapshot=project_snapshot(video,info,candidate,args.task,norm_strategy,result)
                        project_output.write_text(json.dumps(snapshot,indent=2,allow_nan=False)+"\n")
                        entry.update(status="accepted",quality_score=score,quality=metrics,
                                     result_json=str(output),project_json=str(project_output))
                    except Exception as exc: entry.update(status="discarded",reason=str(exc))
                    entries.append(entry)
                entries.sort(key=lambda x:x.get("quality_score",-1),reverse=True)
                accepted=[entry for entry in entries if entry.get("status")=="accepted"]
                if accepted:
                    best_source=Path(accepted[0]["project_json"])
                    best_output=args.output_dir/f"{video.stem}_{args.task}_visionmd_project.json"
                    shutil.copy2(best_source,best_output)
                (args.output_dir/f"{video.stem}_{args.task}_manifest.json").write_text(json.dumps({"video":str(video),"task":args.task,"best_project_json":str(best_output) if accepted else None,"candidates":entries},indent=2)+"\n"); print(f"{video.name}: {sum(x['status']=='accepted' for x in entries)}/{len(entries)} candidates accepted")
        finally: settings.MEDIA_ROOT=original_root

if __name__=="__main__":
    main()
