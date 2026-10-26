"""Conservative experimental persistent 180/360-degree offset repair.
No network or manual angle labels. Ambiguous cases remain review-required.
"""
import numpy as np
from scipy.ndimage import median_filter

def repair_branch(angle, projected, fps):
    y=np.asarray(angle,float);xy=np.asarray(projected,float);diag={'attempted':False,'accepted':False,'reason':'no_excessive_range','events':[]}
    if y.ndim!=1 or xy.ndim!=3 or xy.shape[1]<21 or xy.shape[2]<2 or not np.isfinite(fps) or fps<=0 or len(y)!=len(xy) or len(y)<round(4*fps) or not np.isfinite(y).all() or not np.isfinite(xy).all():
        diag['reason']='insufficient_or_invalid_data';return y.copy(),diag
    xy=xy[:,:,:2]
    robust=float(np.percentile(y,95)-np.percentile(y,5));diag['original_robust_range_deg']=robust
    if robust<=250:return y.copy(),diag
    diag['attempted']=True
    centered=xy-xy[:,:1];scale=np.sqrt(np.mean(np.sum(centered**2,axis=2),axis=1));features=(centered/np.maximum(scale[:,None,None],1e-6)).reshape(len(y),-1)
    if np.any(scale<1e-6):
        diag['reason']='degenerate_projection';return y.copy(),diag
    # Early repeated poses anchor the relative branch; no claim of anatomical zero.
    n=min(round(2.5*fps),len(y)//2);anchors=np.arange(n)
    offsets=[];distances=[]
    for start in range(0,len(y),256):
        dist=np.sqrt(np.mean((features[start:start+256,None]-features[None,anchors])**2,axis=2))
        nearest=np.argsort(dist,axis=1)[:,:5];neighbors=anchors[nearest]
        offsets.append(np.median(y[start:start+256,None]-y[neighbors],axis=1))
        distances.append(np.median(np.take_along_axis(dist,nearest,axis=1),axis=1))
    offset=np.concatenate(offsets);pose_distance=np.concatenate(distances)
    states=np.clip(np.rint(offset/180),-2,2).astype(int);residual=abs(offset-180*states);confident=(pose_distance<.25)&(residual<25)
    width=max(3,round(.25*fps)|1);filtered=median_filter(states,size=width,mode='nearest')
    changes=np.flatnonzero(filtered[1:]!=filtered[:-1])+1;changes=changes[changes>=n]
    if len(changes)!=1:diag['reason']='ambiguous_or_multiple_branch_changes';return y.copy(),diag
    cut=int(changes[0]);old=int(filtered[cut-1]);new=int(filtered[cut]);window=round(.7*fps)
    if old!=0 or new==0 or cut<window or len(y)-cut<window:diag['reason']='unsupported_initial_or_short_branch';return y.copy(),diag
    for lo,hi,state in [(max(n,cut-window),cut,old),(cut,min(len(y),cut+window),new)]:
        valid=confident[lo:hi]
        if valid.sum()<max(5,round(.25*fps)) or np.mean(states[lo:hi][valid]==state)<.85:
            diag['reason']='insufficient_pose_support';return y.copy(),diag
    before=np.flatnonzero(confident[:cut]&(states[:cut]==old));after=np.flatnonzero(confident[cut:]&(states[cut:]==new))+cut
    if not len(before) or not len(after):diag['reason']='unanchored_transition';return y.copy(),diag
    left=int(before[-1]);right=int(after[0])
    if right-left>round(.2*fps):diag['reason']='transition_too_long';return y.copy(),diag
    proposal=y.copy();proposal[cut:]-=180*new
    # Only unsupported transition frames are interpolated; all other samples retain shape.
    proposal[left:right+1]=np.linspace(proposal[left],proposal[right],right-left+1)
    newrange=float(np.percentile(proposal,95)-np.percentile(proposal,5))
    if newrange>250 or newrange<.3*robust:diag['reason']='implausible_repaired_range';return y.copy(),diag
    diag.update(accepted=True,reason='persistent_pose_supported_branch_offset',events=[{'cut_frame':cut,'cut_time_s':cut/fps,'suffix_offset_deg':-180*new,'bridge_start_frame':left,'bridge_end_frame':right}],repaired_robust_range_deg=newrange,changed_frames=int(np.sum(abs(proposal-y)>1e-8)),pose_supported_frames=int(confident.sum()),requires_visual_verification=True)
    return proposal,diag
