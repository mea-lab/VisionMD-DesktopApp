"""Bounded global association fallback for failed hand-localization tracks.
Returns only observed boxes; no interpolated frame counts as a detection.
"""
import numpy as np

def select_recovery_track(samples, *, fps, reference_track, confidences=None):
    if not np.isfinite(fps) or fps<=0:raise ValueError('Invalid frame rate')
    frames=np.array(sorted(samples));step=float(np.median(np.diff(frames))) if len(frames)>1 else 1.
    max_age=.5*fps+step
    reference={int(i):np.asarray(b,float) for i,b in reference_track}
    if not reference:raise RuntimeError('Recovery requires an associated-hand reference track.')
    nodes=[];scores=[];previous=[];active=[]
    for frame,boxes in sorted(samples.items()):
        active=[j for j in active if frame-nodes[j][0]<=max_age]
        added=[]
        for rank,value in enumerate(boxes):
            box=np.asarray(value,float)
            if box.shape!=(4,) or not np.isfinite(box).all() or np.any(box[2:]<=box[:2]):continue
            center=(box[:2]+box[2:])/2;size=max(box[2:]-box[:2])
            if frame in reference:
                rb=reference[frame];rc=(rb[:2]+rb[2:])/2;rs=max(rb[2:]-rb[:2])
                if np.linalg.norm(center-rc)>max(20.,.75*rs):continue
            conf=float(confidences[frame][rank]) if confidences is not None else 1./(rank+1)
            reward=1.+.15*min(1.,max(0.,conf));best=reward;parent=-1
            for j in active:
                old_frame,old_box=nodes[j];age=frame-old_frame
                if age<=0:continue
                old_center=(old_box[:2]+old_box[2:])/2;old_size=max(old_box[2:]-old_box[:2]);dist=float(np.linalg.norm(center-old_center));ratio=size/max(old_size,1.)
                if dist>max(70.,2.5*old_size) or not .4<=ratio<=2.5:continue
                cost=.15*dist/max(old_size,1.)+.1*abs(np.log(ratio))+.8*max(0.,age/step-1.)
                score=scores[j]+reward-cost
                if score>best:best=score;parent=j
            nodes.append((frame,box));scores.append(best);previous.append(parent);added.append(len(nodes)-1)
        active.extend(added)
    if not nodes:raise RuntimeError('No hands were localised.')
    idx=int(np.argmax(scores));track=[]
    while idx>=0:track.append(nodes[idx]);idx=previous[idx]
    track.reverse()
    if len(track)<max(3,int(len(samples)*.5)):raise RuntimeError('No hand track persisted through enough localization frames.')
    return track
