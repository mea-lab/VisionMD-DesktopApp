from rest_framework.decorators import api_view
from rest_framework.response import Response
import json, time
import numpy as np
import scipy.interpolate as interpolate

# Keep the manual-edit schema aligned with PeakfinderSignalAnalyzer.get_output().
STANDARD_FEATURE_KEYS = ("MeanAmplitude", "StdAmplitude", "MeanSpeed", "StdSpeed", "MeanRMSVelocity", "StdRMSVelocity", "MeanOpeningSpeed", "StdOpeningSpeed", "MeanClosingSpeed", "StdClosingSpeed", "MeanMaxOpeningSpeed", "StdMaxOpeningSpeed", "MeanMaxClosingSpeed", "StdMaxClosingSpeed", "MeanCycleDuration", "StdCycleDuration", "CVAmplitude", "CVSpeed", "CVRMSVelocity", "CVOpeningSpeed", "CVClosingSpeed", "CVMaxOpeningSpeed", "CVMaxClosingSpeed", "CVCycleDuration", "Frequency", "AmplitudeDecay", "VelocityDecay", "RangeCycleDuration", "NumberofPauses", "numberofHesitations")

def _mean(values): return float(np.mean(values)) if len(values) else 0.0
def _std(values): return float(np.std(values)) if len(values) else 0.0
def _cv(values): return _std(values) / _mean(values) if _mean(values) else 0.0
def _nearest(times, value): return int(np.abs(times - value).argmin())

def update_standard_features(data):
    """Compute the normal VisionMD feature set from manually edited cycles."""
    velocity = np.asarray(data['velocity_Data'], dtype=float)
    times = np.asarray(data['velocity_Time'], dtype=float)
    fields = [data['valleys_StartTime'], data['valleys_StartData'], data['peaks_Time'], data['peaks_Data'], data['valleys_EndTime'], data['valleys_EndData']]
    cycles = sorted([tuple(float(field[i]) for field in fields) for i in range(min(map(len, fields)))], key=lambda c: c[2])
    cycles = [c for c in cycles if c[0] < c[2] < c[4]]
    if not cycles or not len(velocity) or not len(times): raise ValueError("At least one complete cycle and a velocity signal are required.")
    amplitudes=[]; speeds=[]; rms=[]; opening_speeds=[]; closing_speeds=[]; max_opening=[]; max_closing=[]; durations=[]; pauses=[]; hesitations=0
    max_velocity=float(np.max(np.abs(velocity)))
    for idx,(start_t,start_y,peak_t,peak_y,end_t,end_y) in enumerate(cycles):
        duration=end_t-start_t; baseline=start_y+(end_y-start_y)*(peak_t-start_t)/duration; amplitude=abs(peak_y-baseline)
        start_i,peak_i,end_i=sorted(_nearest(times,value) for value in (start_t,peak_t,end_t))
        movement=velocity[start_i:end_i+1]; opening=velocity[start_i:peak_i+1]; closing=velocity[peak_i:end_i+1]
        amplitudes.append(amplitude); speeds.append(amplitude/duration); rms.append(float(np.sqrt(np.mean(movement**2))))
        opening_speeds.append(amplitude/(peak_t-start_t)); closing_speeds.append(amplitude/(end_t-peak_t)); max_opening.append(float(np.max(np.abs(opening)))); max_closing.append(float(np.max(np.abs(closing)))); durations.append(duration)
        if len(movement)>2 and max_velocity:
            signal_abs=np.abs(movement); threshold=max_velocity*.25; hesitations += int(np.count_nonzero((signal_abs[:-1]<threshold)!=(signal_abs[1:]<threshold))>4)
        if idx+1<len(cycles): pauses.append(max(0.0,cycles[idx+1][0]-end_t))
    peak_times=[c[2] for c in cycles]; frequency=len(cycles)/(cycles[-1][4]-cycles[0][0]) if cycles[-1][4]>cycles[0][0] else 0.0
    range_duration=float(np.ptp(np.diff(peak_times))) if len(peak_times)>2 else 0.0; mean_duration=_mean(durations); mean_pause=_mean(pauses)
    pause_count=sum(x>2*mean_duration for x in durations)+sum(x>2*mean_pause for x in pauses); third=max(1,len(cycles)//3)
    amplitude_decay=_mean(amplitudes[:third])/_mean(amplitudes[-third:]) if _mean(amplitudes[-third:]) else 0.0; velocity_decay=_mean(speeds[:third])/_mean(speeds[-third:]) if _mean(speeds[-third:]) else 0.0
    result={"MeanAmplitude":_mean(amplitudes),"StdAmplitude":_std(amplitudes),"MeanSpeed":_mean(speeds),"StdSpeed":_std(speeds),"MeanRMSVelocity":_mean(rms),"StdRMSVelocity":_std(rms),"MeanOpeningSpeed":_mean(opening_speeds),"StdOpeningSpeed":_std(opening_speeds),"MeanClosingSpeed":_mean(closing_speeds),"StdClosingSpeed":_std(closing_speeds),"MeanMaxOpeningSpeed":_mean(max_opening),"StdMaxOpeningSpeed":_std(max_opening),"MeanMaxClosingSpeed":_mean(max_closing),"StdMaxClosingSpeed":_std(max_closing),"MeanCycleDuration":_mean(durations),"StdCycleDuration":_std(durations),"CVAmplitude":_cv(amplitudes),"CVSpeed":_cv(speeds),"CVRMSVelocity":_cv(rms),"CVOpeningSpeed":_cv(opening_speeds),"CVClosingSpeed":_cv(closing_speeds),"CVMaxOpeningSpeed":_cv(max_opening),"CVMaxClosingSpeed":_cv(max_closing),"CVCycleDuration":_cv(durations),"Frequency":frequency,"AmplitudeDecay":amplitude_decay,"VelocityDecay":velocity_decay,"RangeCycleDuration":range_duration,"NumberofPauses":float(pause_count),"numberofHesitations":float(hesitations)}
    return {key:float(np.nan_to_num(result[key],nan=0.0,posinf=0.0,neginf=0.0)) for key in STANDARD_FEATURE_KEYS}


def updatePeaksAndValleys(inputJson):
    peaksData = inputJson['peaks_Data']
    peaksTime = inputJson['peaks_Time']
    valleysStartData =  inputJson['valleys_StartData'] 
    valleysStartTime =  inputJson['valleys_StartTime']
    valleysEndData =  inputJson['valleys_EndData']
    valleysEndTime =  inputJson['valleys_EndTime']
    velocityData = np.asarray(inputJson['velocity_Data'])
    velocityTime = np.asarray(inputJson['velocity_Time'])

    # Sort valleysStartTime and get the permutation indices
    sorted_indices = sorted(range(len(valleysStartTime)), key=lambda k: valleysStartTime[k])

    # Rearrange valleysStartTime
    valleysStartTime_sorted = sorted(valleysStartTime)

    # Rearrange valleysStartData based on sorted_indices
    valleysStartData_sorted = [valleysStartData[i] for i in sorted_indices]

    # Sort valleysEndTime and get the permutation indices
    sorted_indices_end = sorted(range(len(valleysEndTime)), key=lambda k: valleysEndTime[k])

    # Rearrange valleysEndTime
    valleysEndTime_sorted = sorted(valleysEndTime)

    # Rearrange valleysEndData based on sorted_indices_end
    valleysEndData_sorted = [valleysEndData[i] for i in sorted_indices_end]

    # Sort peaksTime and get the permutation indices
    sorted_indices_peaks = sorted(range(len(peaksTime)), key=lambda k: peaksTime[k])

    # Rearrange peaksTime
    peaksTime_sorted = sorted(peaksTime)

    # Rearrange peaksData based on sorted_indices_peaks
    peaksData_sorted = [peaksData[i] for i in sorted_indices_peaks]

    peaksTime = peaksTime_sorted
    peaksData = peaksData_sorted
    valleysEndTime = valleysEndTime_sorted
    valleysEndData = valleysEndData_sorted
    valleysStartTime = valleysStartTime_sorted
    valleysStartData = valleysStartData_sorted

    amplitude = []
    peakTime = []
    rmsVelocity = []
    speed = []
    averageOpeningSpeed = []
    averageClosingSpeed = []
    cycleDuration = []

    for idx, item in enumerate(peaksData):
        # Height measures
        x1 = valleysStartTime[idx]
        y1 = valleysStartData[idx]

        x2 = valleysEndTime[idx]
        y2 = valleysEndData[idx]

        x = peaksTime[idx]
        y = peaksData[idx]

        f = interpolate.interp1d(np.array([x1, x2]), np.array([y1, y2]))

        amplitude.append(y - f(x))

        # Velocity

        idxStart = (np.abs(velocityTime - x1)).argmin()
        idxEnd = (np.abs(velocityTime - x2)).argmin()
        rmsVelocity.append(np.sqrt(np.mean(velocityData[idxStart:idxEnd] ** 2)))

        speed.append((y - f(x)) / ((valleysEndTime[idx] - valleysStartTime[idx])))
        averageOpeningSpeed.append((y - f(x)) / ((peaksTime[idx] - valleysStartTime[idx])))
        averageClosingSpeed.append((y - f(x)) / ((valleysEndTime[idx] - peaksTime[idx])))
        cycleDuration.append((valleysEndTime[idx] - valleysStartTime[idx]))

        # timming
        peakTime.append(peaksTime[idx] )

    meanAmplitude = np.mean(amplitude)
    stdAmplitude = np.std(amplitude)

    meanSpeed = np.mean(speed)
    stdSpeed = np.std(speed)

    meanRMSVelocity = np.mean(rmsVelocity)
    stdRMSVelocity = np.std(rmsVelocity)
    meanAverageOpeningSpeed = np.mean(averageOpeningSpeed)
    stdAverageOpeningSpeed = np.std(averageOpeningSpeed)
    meanAverageClosingSpeed = np.mean(averageClosingSpeed)
    stdAverageClosingSpeed = np.std(averageClosingSpeed)

    meanCycleDuration = np.mean(cycleDuration)
    stdCycleDuration = np.std(cycleDuration)
    rangeCycleDuration = np.max(np.diff(peakTime)) - np.min(np.diff(peakTime))
    rate = len(valleysEndTime) / (valleysEndTime[-1] - valleysStartTime[0])

    cvAmplitude = stdAmplitude / meanAmplitude
    cvSpeed = stdSpeed / meanSpeed
    cvCycleDuration = stdCycleDuration / meanCycleDuration
    cvRMSVelocity = stdRMSVelocity / meanRMSVelocity
    cvAverageOpeningSpeed = stdAverageOpeningSpeed / meanAverageOpeningSpeed
    cvAverageClosingSpeed = stdAverageClosingSpeed / meanAverageClosingSpeed

    numPeaksHalf = len(peaksData)//2
    rateDecay = (numPeaksHalf / (valleysEndTime[numPeaksHalf] - valleysStartTime[0])) / (numPeaksHalf / (valleysEndTime[-1] - valleysStartTime[numPeaksHalf]))

    amplitudeDecay = np.array(amplitude)[:len(amplitude)//2].mean() / np.array(amplitude)[len(amplitude)//2:].mean()
    velocityDecay = np.array(speed)[:len(speed)//2].mean() / np.array(speed)[len(speed)//2:].mean()

    radarTable = {
            "MeanAmplitude": meanAmplitude,
            "StdAmplitude": stdAmplitude,
            "MeanSpeed": meanSpeed,
            "StdSpeed": stdSpeed,
            "MeanRMSVelocity": meanRMSVelocity,
            "StdRMSVelocity": stdRMSVelocity,
            "MeanOpeningSpeed": meanAverageOpeningSpeed,
            "stdOpeningSpeed": stdAverageOpeningSpeed,
            "meanClosingSpeed": meanAverageClosingSpeed,
            "stdClosingSpeed": stdAverageClosingSpeed,
            "meanCycleDuration": meanCycleDuration,
            "stdCycleDuration": stdCycleDuration,
            "rangeCycleDuration": rangeCycleDuration,
            "rate": rate,
            "amplitudeDecay": amplitudeDecay,
            "velocityDecay": velocityDecay,
            "rateDecay": rateDecay,
            "cvAmplitude": cvAmplitude,
            "cvCycleDuration": cvCycleDuration,
            "cvSpeed": cvSpeed,
            "cvRMSVelocity" : cvRMSVelocity,
            "cvOpeningSpeed": cvAverageOpeningSpeed,
            "cvClosingSpeed": cvAverageClosingSpeed
        }
    
    return radarTable

@api_view(['POST'])
def updatePlotData(request):
    try:
        json_data = json.loads(request.POST['json_data'])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON data")

    try:
        print("Updating plot started")
        start_time = time.time()
        outputDict = update_standard_features(json_data)
        print("Plot updated in %s seconds" % (time.time() - start_time))
        result = outputDict
    except Exception as e:
        print(f"Error in updatePlotData: {e}")
        result = {'error': str(e)}

    return Response(result)
