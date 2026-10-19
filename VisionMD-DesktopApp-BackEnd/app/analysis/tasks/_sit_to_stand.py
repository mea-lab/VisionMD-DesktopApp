"""Frontal single-rise descriptors, ported from the exploratory chair study.

No clinical score or diagnosis is inferred. Saved landmarks are the only input
when reviewing boundaries. Primary kinematic definitions retain their original
5–95% window unless a reviewer explicitly changes the rise interval.
"""
import numpy as np
from scipy.signal import butter, sosfiltfilt, find_peaks

VERSION = "sit-to-stand-v1"

def fill(x):
 x=np.asarray(x,float);flat=x.reshape(len(x),-1);out=flat.copy()
 for j in range(flat.shape[1]):
  valid=np.isfinite(flat[:,j])
  if valid.sum()<3:raise ValueError('Too few finite landmarks')
  out[:,j]=np.interp(np.arange(len(x)),np.flatnonzero(valid),flat[valid,j])
 return out.reshape(x.shape)

def smooth(x,fps):
 x=fill(x);sos=butter(3,min(4.,fps*.2),fs=fps,btype='low',output='sos')
 return sosfiltfilt(sos,x,axis=0) if len(x)>15 else x

def events_for(hip,ankles,fps):
 height=smooth(ankles[:,1]-hip[:,1],fps);lo,hi=np.percentile(height,[5,95]);amplitude=hi-lo
 if amplitude<=0:raise ValueError('No pelvis ascent')
 q=(height-lo)/amplitude;events=[]
 valleys,_=find_peaks(-q,prominence=.20,distance=max(1,round(.4*fps)))
 valleys=np.unique(np.r_[int(np.argmin(q[:max(2,round(.4*fps))])),valleys])
 peaks,_=find_peaks(q,prominence=.35,distance=max(1,round(.5*fps)))
 # A final standing plateau need not have a subsequent descent to be a peak.
 final_valley=int(valleys[-1]);peaks=np.unique(np.r_[peaks,final_valley+int(np.argmax(q[final_valley:]))])
 basins={}
 for peak in peaks:
  before=valleys[valleys<peak]
  if not len(before):continue
  valley=int(before[-1]);exc=q[peak]-q[valley]
  if exc<.35:continue
  if valley not in basins or q[peak]>q[basins[valley]]:basins[valley]=int(peak)
 for valley,peak in sorted(basins.items()):
  local=(q[valley:peak+1]-q[valley])/(q[peak]-q[valley])
  a=valley+int(np.flatnonzero(local>=.10)[0]);b=valley+int(np.flatnonzero(local>=.90)[0])
  start=valley+int(np.flatnonzero(local>=.05)[0]);end=valley+int(np.flatnonzero(local>=.95)[0])
  if b-a<max(2,int(.12*fps)):continue
  events.append(dict(start_frame=start,end_frame=end,start_10=a,end_90=b,duration_10_90=(b-a)/fps,duration_05_95=(end-start)/fps))
 return height,q,events

def extract_2d(points,kind,fps):
 if kind=='mp':
  points=points.copy();points[np.minimum(points[:,:,2],points[:,:,3])<.30,:2]=np.nan
  shoulder=np.mean(points[:,[11,12],:2],axis=1);hip=np.mean(points[:,[23,24],:2],axis=1);ankle=np.mean(points[:,[27,28],:2],axis=1);head=points[:,0,:2];wrists=points[:,[15,16],:2];sh=points[:,[11,12],:2]
 else:
  shoulder=np.mean(points[:,[2,5]],axis=1);hip=points[:,14];ankle=np.mean(points[:,[10,13]],axis=1);head=points[:,16];wrists=points[:,[4,7]];sh=points[:,[2,5]]
 missing=1-np.mean(np.all(np.isfinite(hip),axis=1)&np.all(np.isfinite(ankle),axis=1))
 if missing>.10:raise ValueError('More than 10% pelvis/ankle observations missing or low-confidence')
 hip=smooth(hip,fps);ankle=smooth(ankle,fps);shoulder=smooth(shoulder,fps)
 height,q,events=events_for(hip,ankle,fps)
 if not events:raise ValueError('No complete 10–90% pelvis ascent')
 # Preserve all transitions; use the first completed rise for the initial single-rise feature.
 ev=events[0];a,b=ev['start_frame'],ev['end_frame'];end=min(len(q),b+max(3,round(.3*fps)))
 scale=float(np.median(np.linalg.norm(shoulder[b:end]-ankle[b:end],axis=1)))
 if scale<1:raise ValueError('Degenerate image-space reference')
 excursion=float(height[b]-height[a])/scale
 if not .12<excursion<1.5:raise ValueError('Pelvis excursion inconsistent with a clear rise')
 segment=slice(a,b+1);vertical=smooth(height/scale,fps);speed=np.gradient(vertical)*fps;trunk=shoulder-hip;lean=np.degrees(np.arctan2(trunk[:,0],-trunk[:,1]));lateral=(hip[:,0]-ankle[:,0])/scale
 # Image-space arm geometry is a movement descriptor, not proof of contact/support.
 try:
  wrist=fill(wrists);shoulderwidth=np.linalg.norm(sh[:,0]-sh[:,1],axis=1);crossdist=(np.linalg.norm(wrist[:,0]-sh[:,1],axis=1)+np.linalg.norm(wrist[:,1]-sh[:,0],axis=1))/(2*np.maximum(shoulderwidth,1))
 except ValueError:crossdist=np.full(len(hip),np.nan)
 s=speed[segment];features=dict(ascent_time_10_90=ev['duration_10_90'],ascent_time_05_95=ev['duration_05_95'],completed_ascent_count=len(events),total_first_to_last_ascent=(events[-1]['end_frame']-events[0]['start_frame'])/fps,pelvis_excursion_relative=excursion,mean_ascent_speed_relative=float(np.mean(s)),p95_ascent_speed_relative=float(np.percentile(s,95)),ascent_speed_cv=float(np.std(s)/max(np.mean(s),1e-6)),lateral_shift_relative=float(np.ptp(lateral[segment])),trunk_lateral_rom_deg=float(np.ptp(lean[segment])),arm_cross_distance_mean=float(np.mean(crossdist[segment])),arm_cross_distance_change=float(np.ptp(crossdist[segment])))
 return features,dict(events=events,excursion_relative=excursion,missing_fraction=float(missing),scale_px=scale),dict(height=height,q=q,hip=hip,ankles=ankle,lean=lean)

FEATURE_LABELS = {
    "ascent_time_10_90": "Central ascent time 10–90% (s)",
    "ascent_speed_cv": "Ascent velocity coefficient of variation",
    "lateral_shift_relative": "Lateral pelvis range (relative)",
    "trunk_lateral_rom_deg": "Trunk lateral angular range (deg)",
    "pelvis_excursion_relative": "Pelvis excursion (relative)",
    "arm_cross_distance_mean": "Mean crossed-arm distance (relative)",
    "arm_cross_distance_change": "Crossed-arm distance range (relative)",
    "combined_preparation_to_pelvis_end_s": "Preparation to pelvic movement end (s)",
    "combined_preparation_before_ascent_s": "Preparation lead-in (s)",
    "extra_speed_peaks": "Extra pelvis speed peaks",
}


def runs(mask):
    edges = np.diff(np.r_[False, mask, False].astype(int))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))


def lowpass(values, fps, hz):
    return sosfiltfilt(butter(3, min(hz, fps * .2), fs=fps, output='sos'), fill(values), axis=0)


def automatic_boundaries(points, fps, event):
    p = lowpass(points, fps, 4)
    hip = p[:, 14]
    shoulder = p[:, [2, 5]].mean(axis=1)
    nb = max(5, round(.25 * fps))
    rel = shoulder - hip
    torso = float(np.median(np.linalg.norm(rel[:nb], axis=1)))
    if torso <= 1:
        raise ValueError('Cannot estimate the initial torso reference. Review full-body tracking.')
    dep_p = abs((-hip[:, 1] - np.median(-hip[:nb, 1])) / torso)
    dep_s = np.linalg.norm((rel - np.median(rel[:nb], axis=0)) / torso, axis=1)
    def threshold(values, floor):
        base = values[:nb]
        med = np.median(base)
        return max(floor, med + 4 * 1.4826 * np.median(abs(base - med)))
    tp, ts = threshold(dep_p, .025), threshold(dep_s, .05)
    # Inherited upward bout: original study uses a separately filtered 3-Hz
    # normalized ankle-relative height and the first completed candidate.
    p3 = lowpass(points, fps, 3)
    h3 = p3[:, [10, 13], 1].mean(axis=1) - p3[:, 14, 1]
    lo, hi = np.percentile(h3, [5, 95])
    q = (h3 - lo) / max(hi - lo, 1e-8)
    # Same candidate search, without the extra 4-Hz height filtering.
    valleys, _ = find_peaks(-q, prominence=.20, distance=max(1, round(.4*fps)))
    valleys = np.unique(np.r_[np.argmin(q[:max(2, round(.4*fps))]), valleys])
    peaks, _ = find_peaks(q, prominence=.35, distance=max(1, round(.5*fps)))
    peaks = np.unique(np.r_[peaks, valleys[-1]+np.argmax(q[valleys[-1]:])])
    basins = {}
    for peak in peaks:
        before = valleys[valleys < peak]
        if len(before):
            valley = int(before[-1])
            if q[peak]-q[valley] >= .35 and (valley not in basins or q[peak] > q[basins[valley]]):
                basins[valley] = int(peak)
    a10, b90 = event['start_10'], event['end_90']
    for valley, peak in sorted(basins.items()):
        local = (q[valley:peak+1]-q[valley])/(q[peak]-q[valley])
        a = valley + np.flatnonzero(local >= .1)[0]
        b = valley + np.flatnonzero(local >= .9)[0]
        if b-a >= max(2, int(.12*fps)):
            a10, b90 = int(a), int(b)
            break
    velocity = np.gradient(q)*fps
    anchor = a10 + int(np.argmax(velocity[a10:b90+1]))
    if velocity[anchor] < .10:
        raise ValueError('No clear upward-velocity anchor. Choose a complete seated-to-standing interval.')
    moving = velocity >= max(.10, .12*velocity[anchor])
    for a, b in runs(~moving):
        if a > 0 and b < len(moving) and b-a <= round(.10*fps):
            moving[a:b] = True
    bout = next(a for a, b in runs(moving) if a <= anchor < b)
    mask = (dep_p > tp) | (dep_s > ts)
    hold = int(np.ceil(.10*fps))
    prep = next((j for j in range(nb, anchor-hold+2) if mask[j:j+hold].all()), None)
    flags = []
    if prep is None:
        flags.append('Preparation onset not resolved; upward ascent used provisionally.')
        prep = bout
    if prep > bout:
        flags.append('Preparation candidate occurs after upward ascent; review the boundaries.')
    if np.ptp(dep_p[:nb]) > .025 or np.ptp(dep_s[:nb]) > .05:
        flags.append('Initial baseline is moving; review preparation onset.')
    y = -hip[:, 1]
    v = np.gradient(y, 1/fps, edge_order=2)
    lo, hi = max(0, anchor-round(.25*fps)), min(len(y), anchor+round(.25*fps)+1)
    peak = lo + int(np.argmax(v[lo:hi]))
    quiet = abs(v) <= .1*v[peak]
    old_a, old_b = event['start_frame'], event['end_frame']
    candidates = [(a,b) for a,b in runs(quiet[:min(old_a, peak)+1])
                  if b-a >= max(2, round(.1*fps)) and b >= max(0, old_a-round(.75*fps))]
    a = candidates[-1][1]-1 if candidates else old_a
    stop = min(len(y), old_b+round(.5*fps)+1)
    target = y[a]+.85*(np.percentile(y[peak:stop],95)-y[a])
    end = None
    for s,e in runs(quiet[peak:stop]):
        s += peak; e += peak
        if e-s >= max(3,round(.2*fps)) and np.median(y[s:e]) >= target:
            end = s+round(.1*fps)
            break
    if end is None:
        end = old_b
        flags.append('No sustained pelvic quiet interval; endpoint uses the 95% crossing.')
    bounds = dict(preparation_start=prep/fps, rise_start=bout/fps, rise_end=end/fps)
    return bounds, dep_p/tp, dep_s/ts, flags


def analyze(poses, fps, start_time=0., boundaries=None, automatic=None):
    fps, start_time = float(fps), float(start_time)
    p = np.asarray(poses, dtype=float)
    if not np.isfinite(fps) or fps < 10 or not np.isfinite(start_time):
        raise ValueError('A finite frame rate of at least 10 fps and start time are required.')
    if p.ndim != 3 or p.shape[1:] != (17,2) or len(p) < max(20, round(.8*fps)):
        raise ValueError('Select a complete rise with at least 0.8 seconds of valid 17-point landmarks.')
    measured, info, trace = extract_2d(p, 'metrabs', fps)
    event = info['events'][0]
    detected, pelvis_evidence, shoulder_evidence, flags = automatic_boundaries(p, fps, event)
    auto = {k: float(v+start_time) for k,v in detected.items()}
    if automatic is not None:
        auto = dict(automatic)
    applied = dict(auto if boundaries is None else boundaries)
    keys = ('preparation_start', 'rise_start', 'rise_end')
    if set(applied) != set(keys):
        raise ValueError('Provide preparation onset, upward-ascent onset and pelvic movement end.')
    applied = {k: float(applied[k]) for k in keys}
    end_time = start_time+(len(p)-1)/fps
    if any(not np.isfinite(v) or v < start_time or v > end_time for v in applied.values()):
        raise ValueError('Boundaries must be finite and inside the cached recording.')
    if boundaries is not None and not (applied[keys[0]] <= applied[keys[1]] < applied[keys[2]]):
        raise ValueError('Use preparation onset ≤ upward-ascent onset < pelvic movement end.')
    a,b = event['start_frame'],event['end_frame']
    window_source = 'automatic_5_95'
    # Preparation-only edits do not redefine the legacy motion window.
    if boundaries is not None and any(abs(applied[k]-auto[k]) > .25/fps for k in ('rise_start','rise_end')):
        a = int(round((applied['rise_start']-start_time)*fps))
        b = int(round((applied['rise_end']-start_time)*fps))
        if b-a < 3:
            raise ValueError('The rise interval must contain at least four frames.')
        window_source = 'reviewed_rise_interval'
        H, P, A = trace['height'],trace['hip'],trace['ankles']
        S = smooth(p[:,[2,5]].mean(axis=1), fps)
        L = float(np.median(np.linalg.norm(S[b:min(len(p),b+max(3,round(.3*fps)))]-A[b:min(len(p),b+max(3,round(.3*fps)))],axis=1)))
        if L < 1 or H[b] <= H[a]:
            raise ValueError('The reviewed interval must contain a positive pelvis rise and valid reference.')
        v = np.gradient(smooth(H/L,fps))*fps
        lateral = (P[:,0]-A[:,0])/L
        theta = np.degrees(np.arctan2((S-P)[:,0],-(S-P)[:,1]))
        sh = p[:,[2,5]]
        wrists = fill(p[:,[4,7]])
        cross = (np.linalg.norm(wrists[:,0]-sh[:,1],axis=1)+np.linalg.norm(wrists[:,1]-sh[:,0],axis=1))/(2*np.maximum(np.linalg.norm(sh[:,0]-sh[:,1],axis=1),1))
        seg = slice(a,b+1)
        measured.update(ascent_speed_cv=float(np.std(v[seg])/max(np.mean(v[seg]),1e-6)),lateral_shift_relative=float(np.ptp(lateral[seg])),trunk_lateral_rom_deg=float(np.ptp(theta[seg])),pelvis_excursion_relative=float((H[b]-H[a])/L),arm_cross_distance_mean=float(np.mean(cross[seg])),arm_cross_distance_change=float(np.ptp(cross[seg])))
        info['scale_px'] = L
    L = info['scale_px']
    y = -lowpass(p, fps, 4)[:,14,1]
    velocity = np.gradient(y,1/fps,edge_order=2)
    peaks,_ = find_peaks(abs(velocity[a:b+1]),prominence=.1*np.max(abs(velocity[a:b+1])),distance=max(1,round(.12*fps)))
    measured['extra_speed_peaks'] = max(0,len(peaks)-1)
    measured['combined_preparation_to_pelvis_end_s'] = applied['rise_end']-applied['preparation_start']
    lead = applied['rise_start']-applied['preparation_start']
    measured['combined_preparation_before_ascent_s'] = lead if lead >= 0 else None
    if lead < 0 and not any('after upward ascent' in flag for flag in flags):
        flags.append('Preparation candidate occurs after upward ascent; review the boundaries.')
    time = (start_time+np.arange(len(p))/fps).tolist()
    values = {key: measured[key] for key in FEATURE_LABELS}
    features = {FEATURE_LABELS[k]:v for k,v in values.items()}
    height = trace['height']/L
    result = {
        **features,
        'linePlot': {'time':time,'data':height.tolist()},
        'velocityPlot': {'time':time,'data':velocity.tolist()},
        'rawData': {'time':time,'data':(p[:,[10,13],1].mean(axis=1)-p[:,14,1]).tolist()},
        'radarTable':features,
        'peaks':{'time':[],'data':[]},'valleys_start':{'time':[],'data':[]},'valleys_end':{'time':[],'data':[]},
        'landMarks':p.tolist(),'allLandMarks':p.tolist(),
        'landmark_start_frame':round(start_time*fps),'landmark_fps':fps,
        'normalization_factor':L,
        'sit_to_stand': {
            'version':VERSION,'features':values,'automatic_boundaries':auto,'boundaries':applied,
            'reviewed':boundaries is not None,
            'feature_window':{'start':time[a],'end':time[b],'source':window_source},
            'central_ascent':{'start':time[event['start_10']],'end':time[event['end_90']]},
            'signals':{'time':time,'pelvis_height':height.tolist(),'pelvis_evidence':pelvis_evidence.tolist(),'shoulder_evidence':shoulder_evidence.tolist(),'pelvis_velocity':velocity.tolist()},
            'speed_peaks':{'time':[time[a+i] for i in peaks],'data':velocity[a+peaks].tolist()},
            'quality':{'requires_visual_review':True,'warnings':flags,'hand_support':'not_assessed','metric_scaling':'not_applied','endpoint':'pelvic movement end; full upright posture not confirmed'},
        },
        'sit_to_stand_analysis_cache': {'version':VERSION,'fps':fps,'start_time':start_time,'poses2d':p.tolist(),'automatic_boundaries':auto},
    }
    return clean(result)


def clean(value):
    if isinstance(value,dict):
        return {k:clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [clean(v) for v in value]
    if isinstance(value,(float,np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value,np.integer):
        return int(value)
    return value
