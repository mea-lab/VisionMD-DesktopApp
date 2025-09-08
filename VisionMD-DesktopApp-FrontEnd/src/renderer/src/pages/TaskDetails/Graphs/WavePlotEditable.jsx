import React, { useState, useRef, useEffect } from 'react';
import Plot from 'react-plotly.js';
import Button from '@mui/material/Button';

const WavePlotEditable = ({
  selectedTaskIndex,
  tasks,
  setTasks,
  videoRef,
  startTime,
  endTime,
  handleJSONUpload,
}) => {
  const [currentData, setCurrentData] = useState(tasks?.[selectedTaskIndex]?.data);

  useEffect(() => {
    setCurrentData(tasks[selectedTaskIndex].data);
    setDataRevision((r) => r + 1);
  }, [tasks?.[selectedTaskIndex]?.data, selectedTaskIndex]);

  const [videoCurrentTime, setVideoCurrentTime] = useState(startTime);
  const [blurEnd, setBlurEnd] = useState(startTime);
  const [blurStart, setBlurStart] = useState(endTime);

  const [popup, setPopup] = useState({ msg: '', show: false });
  const [alertPopup, setAlertPopup] = useState({ msg: '', show: false });

  const [taskFlags, setTaskFlags] = useState({ addNew: false, remove: false });
  const [addPointName, setAddPointName] = useState('valley_start');
  const [isMarkUp, setIsMarkUp] = useState(false);

  const [tempCycle, setTempCycle] = useState({
    valleyStart: null,
    peak: null,
  });

  const [dataRevision, setDataRevision] = useState(0);
  const [uiRevision, setUiRevision] = useState("stable");

  // For quick-add (Q, W, E)
  const [quickAdd, setQuickAdd] = useState({
    peakHigh: false,
    peakLowStart: false,
    peakLowEnd: false,
  });

  const [selectedPoint, setSelectedPoint] = useState({});
  const [isKeyDown, setIsKeyDown] = useState(false);

  const plotRef = useRef(null);

  // ------------------ Update tasks ------------------
  const updateCurrentTaskData = (updatedData) => {
    const updatedTasks = [...tasks];
    updatedTasks[selectedTaskIndex] = {
      ...updatedTasks[selectedTaskIndex],
      data: updatedData,
    };
    setTasks(updatedTasks);
  };

  // ------------------ Video event handlers ------------------
  useEffect(() => {
    const videoEl = videoRef.current;
    let frameId = null;

    const updateFrame = () => {
      if (!videoEl.paused && !videoEl.ended) {
        setVideoCurrentTime(videoEl.currentTime);
        frameId = requestAnimationFrame(updateFrame);
      }
    };

    const playHandler = () => {
      if (!frameId) frameId = requestAnimationFrame(updateFrame);
    };

    const pauseHandler = () => {
      if (frameId) {
        cancelAnimationFrame(frameId);
        frameId = null;
      }
      setVideoCurrentTime(videoEl.currentTime);
    };

    const timeUpdateHandler = () => {
      setVideoCurrentTime(videoEl.currentTime);
    };

    videoEl.addEventListener('play', playHandler);
    videoEl.addEventListener('pause', pauseHandler);
    videoEl.addEventListener('ended', pauseHandler);
    videoEl.addEventListener('timeupdate', timeUpdateHandler);

    return () => {
      videoEl.removeEventListener('play', playHandler);
      videoEl.removeEventListener('pause', pauseHandler);
      videoEl.removeEventListener('ended', pauseHandler);
      videoEl.removeEventListener('timeupdate', timeUpdateHandler);
      if (frameId) cancelAnimationFrame(frameId);
    };
  }, [videoRef]);

  // ------------------ Keyboard handlers ------------------
  useEffect(() => {
    const keyDownHandler = (evt) => {
      if (!isKeyDown) {
        setIsKeyDown(true);
        if (evt.code === 'Escape') cancelCurrentTask();
        else if (evt.code === 'KeyQ')
          setQuickAdd((q) => ({ ...q, peakHigh: true }));
        else if (evt.code === 'KeyW')
          setQuickAdd((q) => ({ ...q, peakLowStart: true }));
        else if (evt.code === 'KeyE')
          setQuickAdd((q) => ({ ...q, peakLowEnd: true }));
      }
    };

    const keyUpHandler = (evt) => {
      setIsKeyDown(false);
      if (evt.code === 'KeyQ')
        setQuickAdd((q) => ({ ...q, peakHigh: false }));
      if (evt.code === 'KeyW')
        setQuickAdd((q) => ({ ...q, peakLowStart: false }));
      if (evt.code === 'KeyE')
        setQuickAdd((q) => ({ ...q, peakLowEnd: false }));
    };

    document.addEventListener('keydown', keyDownHandler);
    document.addEventListener('keyup', keyUpHandler);

    return () => {
      document.removeEventListener('keydown', keyDownHandler);
      document.removeEventListener('keyup', keyUpHandler);
    };
  }, [isKeyDown]);

  // ------------------ Helpers / Popups ------------------
  const cancelCurrentTask = () => {
    setPopup({ msg: '', show: false });
    setAlertPopup({ msg: '', show: false });
    setTaskFlags({ addNew: false, remove: false });
    setSelectedPoint({});
    setAddPointName('valley_start');
    setTempCycle({ valleyStart: null, peak: null });
    resetBlur();
  };

  const resetBlur = () => {
    setBlurEnd(startTime);
    setBlurStart(endTime);
  };

  const showPopUp = (msg) => setPopup({ msg, show: true });

  // ------------------ Overlap checks ------------------
  const isInAnyExistingCycle = (x) => {
    const starts = currentData.valleys_start.time;
    const ends = currentData.valleys_end.time;
    return starts.some((s, i) => x >= s && x <= ends[i]);
  };

  const intervalsOverlap = (aStart, aEnd, bStart, bEnd) => {
    return aStart < bEnd && bStart < aEnd;
  };

  const isOverlappingExistingCycle = (newStart, newEnd) => {
    const starts = currentData.valleys_start.time;
    const ends = currentData.valleys_end.time;
    for (let i = 0; i < starts.length; i++) {
      if (intervalsOverlap(newStart, newEnd, starts[i], ends[i])) {
        return true;
      }
    }
    return false;
  };

  // ------------------ Plot click handler ------------------
  const handleClickOnPlot = (plotClickData) => {
    const { x, y, data: plotSeries } = plotClickData.points[0];
    videoRef.current.currentTime = x;
    videoRef.current.pause();

    // Quick-add logic
    if (quickAdd.peakHigh || quickAdd.peakLowStart || quickAdd.peakLowEnd) {
      handleQuickAdd(x, y);
      return;
    }

    // Add new cycle logic
    if (!isMarkUp && taskFlags.addNew) {
      addNewPeakAndValley({ x, y });
      return;
    }

    // Remove cycle logic
    if (!isMarkUp && taskFlags.remove) {
      const name = plotSeries.name;
      if (['Peak values', 'Valley start', 'Valley end'].includes(name)) {
        const idx = findIndexForClickedPoint(name, x, y);
        if (idx !== -1) {
          setSelectedPoint({ idx, name });
          setPopup({ msg: '', show: false });
          setAlertPopup({
            msg: 'All points in this cycle will be removed. Are you sure?',
            show: true,
          });
        }
      }
      return;
    }

    // Repositioning existing points logic
    if (!isMarkUp) {
      const name = plotSeries.name;
      if (['peak values', 'valley start', 'valley end'].includes(name)) {
        const found = handleSelectElementFromArray(name, x);
        if (found) setSelectedPoint(found);
      }
      setDataRevision((r) => r + 1);
    } else if (isMarkUp && selectedPoint.name === 'peak values') {
      // repositioning an existing peak
      const idx = selectedPoint.idx;
      if (
        x > currentData.valleys_start.time[idx] &&
        x < currentData.valleys_end.time[idx]
      ) {
        const newPeaks = {
          data: currentData.peaks.data.map((d, i) => (i === idx ? y : d)),
          time: currentData.peaks.time.map((t, i) => (i === idx ? x : t)),
        };
        updateCurrentTaskData({ ...currentData, peaks: newPeaks });
        setSelectedPoint({});
        resetBlur();
        setIsMarkUp(false);
        setDataRevision((r) => r + 1);
      } else {
        showPopUp('Peak must lie within the valley start/end range.');
      }
    }
  };

  // ------------------ Step-by-step "Add Cycle" ------------------
  const addNewPeakAndValley = ({ x, y }) => {
    if (addPointName === 'valley_start') {
      // 1) Validate valley start
      if (isInAnyExistingCycle(x)) {
        showPopUp('You are trying to place a valley start that overlaps another cycle.');
        return;
      }
      // Store to tempCycle and show it immediately
      setTempCycle({ valleyStart: { x, y }, peak: null });
      setAddPointName('peak');
      showPopUp('Next, select the new peak point.');
      setDataRevision((r) => r + 1);

    } else if (addPointName === 'peak') {
      // 2) Validate peak
      if (!tempCycle.valleyStart) {
        showPopUp('No valley start found. Please cancel and try again.');
        return;
      }
      if (x <= tempCycle.valleyStart.x) {
        showPopUp('Peak time must be after the Valley Start time.');
        return;
      }
      if (isOverlappingExistingCycle(tempCycle.valleyStart.x, x)) {
        showPopUp('Peak is overlapping with an existing cycle range.');
        return;
      }
      // Store peak in tempCycle => displayed immediately
      setTempCycle((prev) => ({ ...prev, peak: { x, y } }));
      setAddPointName('valley_end');
      showPopUp('Finally, select the new valley end point.');
      setDataRevision((r) => r + 1);

    } else if (addPointName === 'valley_end') {
      // 3) Validate valley end
      if (!tempCycle.valleyStart || !tempCycle.peak) {
        showPopUp('No valley start or peak found. Please cancel and try again.');
        return;
      }
      if (x <= tempCycle.peak.x) {
        showPopUp('Valley end time must be after the Peak time.');
        return;
      }
      if (isOverlappingExistingCycle(tempCycle.peak.x, x)) {
        showPopUp('Valley end is overlapping with an existing cycle range.');
        return;
      }

      // If valid => commit all three to currentData
      const newValleysStart = {
        data: [...currentData.valleys_start.data, tempCycle.valleyStart.y],
        time: [...currentData.valleys_start.time, tempCycle.valleyStart.x],
      };
      const newPeaks = {
        data: [...currentData.peaks.data, tempCycle.peak.y],
        time: [...currentData.peaks.time, tempCycle.peak.x],
      };
      const newValleysEnd = {
        data: [...currentData.valleys_end.data, y],
        time: [...currentData.valleys_end.time, x],
      };

      const updatedData = {
        ...currentData,
        valleys_start: newValleysStart,
        peaks: newPeaks,
        valleys_end: newValleysEnd,
      };

      updateCurrentTaskData(updatedData);
      updateRadarTable(updatedData);
      handleJSONUpload(true, updatedData);

      // Reset so we can add another cycle if we want
      cancelCurrentTask();
      setDataRevision((r) => r + 1);
    }
  };

  // ------------------ Remove cycle logic ------------------
  const removePeakAndValley = () => {
    const idx = selectedPoint.idx;
    if (idx < 0 || idx >= currentData.peaks.data.length) return;

    const newPeaks = {
      data: currentData.peaks.data.filter((_, i) => i !== idx),
      time: currentData.peaks.time.filter((_, i) => i !== idx),
    };
    const newValleyStart = {
      data: currentData.valleys_start.data.filter((_, i) => i !== idx),
      time: currentData.valleys_start.time.filter((_, i) => i !== idx),
    };
    const newValleyEnd = {
      data: currentData.valleys_end.data.filter((_, i) => i !== idx),
      time: currentData.valleys_end.time.filter((_, i) => i !== idx),
    };

    const updatedData = {
      ...currentData,
      peaks: newPeaks,
      valleys_start: newValleyStart,
      valleys_end: newValleyEnd,
    };
    updateCurrentTaskData(updatedData);
    handleJSONUpload(true, updatedData);
    updateRadarTable(updatedData);

    cancelCurrentTask();
    setDataRevision((r) => r + 1);
  };

  const continueAlert = () => {
    setAlertPopup({ msg: '', show: false });
    removePeakAndValley();
  };

  // ------------------ Quick-add logic (Q, W, E) ------------------
  const handleQuickAdd = (x, y) => {
    const dataCopy = { ...currentData };
    if (quickAdd.peakHigh) {
      dataCopy.peaks.data.push(y);
      dataCopy.peaks.time.push(x);
      setQuickAdd((q) => ({ ...q, peakHigh: false }));
    } else if (quickAdd.peakLowStart) {
      dataCopy.valleys_start.data.push(y);
      dataCopy.valleys_start.time.push(x);
      setQuickAdd((q) => ({ ...q, peakLowStart: false }));
    } else if (quickAdd.peakLowEnd) {
      dataCopy.valleys_end.data.push(y);
      dataCopy.valleys_end.time.push(x);
      setQuickAdd((q) => ({ ...q, peakLowEnd: false }));
    }
    updateCurrentTaskData(dataCopy);
    setDataRevision((r) => r + 1);
    updateRadarTable(dataCopy);
  };

  // ------------------ Helpers for picking existing points ------------------
  const getPointArrays = (name) => {
    if (name === 'Peak values') return currentData.peaks;
    if (name === 'Valley start') return currentData.valleys_start;
    if (name === 'Valley end') return currentData.valleys_end;
    return { data: [], time: [] };
  };

  const findIndexForClickedPoint = (name, xVal, yVal) => {
    const { data, time } = getPointArrays(name);
    const idx = time.indexOf(xVal);
    return idx !== -1 && data[idx] === yVal ? idx : -1;
  };

  const handleSelectElementFromArray = (name, xVal) => {
    const { data, time } = getPointArrays(name);
    const idx = time.indexOf(xVal);
    if (idx >= 0) {
      setIsMarkUp(true);
      if (name === 'peak values') {
        setBlurEnd(currentData.valleys_start.time[idx]);
        setBlurStart(currentData.valleys_end.time[idx]);
      }
      return { peak_data: [data[idx]], peak_time: [time[idx]], idx, name };
    }
    return null;
  };

  // ------------------ Update radar table ------------------
  const updateRadarTable = async (dataToUse = null) => {
    try {
      const dataForUpdate = dataToUse || currentData;
      const jsonData = JSON.stringify({
        peaks_Data: dataForUpdate.peaks.data,
        peaks_Time: dataForUpdate.peaks.time,
        valleys_StartData: dataForUpdate.valleys_start.data,
        valleys_StartTime: dataForUpdate.valleys_start.time,
        valleys_EndData: dataForUpdate.valleys_end.data,
        valleys_EndTime: dataForUpdate.valleys_end.time,
        velocity_Data: dataForUpdate.velocityPlot.data,
        velocity_Time: dataForUpdate.velocityPlot.time,
      });
      const uploadData = new FormData();
      uploadData.append('json_data', jsonData);
      const response = await fetch('http://localhost:8000/api/update_plot/', {
        method: 'POST',
        body: uploadData,
      });
      if (response.ok) {
        const data = await response.json();
        const newJsonData = {
          ...dataForUpdate,
          radarTable: data,
        };
        updateCurrentTaskData(newJsonData);
        handleJSONUpload(true, newJsonData);
      } else {
        throw new Error('Server responded with an error!');
      }
    } catch (error) {
      console.error('Failed to update plot data:', error);
    }
  };

  // ------------------ Plotly shapes ------------------
  const shapes = [
    {
      type: 'line',
      x0: videoCurrentTime,
      y0: 0,
      x1: videoCurrentTime,
      y1: 1,
      xref: 'x',
      yref: 'paper',
      line: { color: 'grey', width: 1 },
      layer: 'below',
    },
    {
      type: 'rect',
      x0: startTime,
      y0: Math.min(...currentData.linePlot.data),
      x1: blurEnd,
      y1: Math.max(...currentData.linePlot.data),
      fillcolor: 'rgba(128, 128, 128, 0.4)',
      line: { width: 0 },
      layer: 'above',
    },
    {
      type: 'rect',
      x0: blurStart,
      y0: Math.min(...currentData.linePlot.data),
      x1: endTime,
      y1: Math.max(...currentData.linePlot.data),
      fillcolor: 'rgba(128, 128, 128, 0.4)',
      line: { width: 0 },
      layer: 'above',
    },
  ];

  return (
    <div
      className="relative flex flex-col items-center pr-8 pl-8 pb-8"
    >
      <div
        className="w-full max-w-5xl p-4 bg-[#333338] rounded-xl"
        style={{ minHeight: '400px' }}
      >
        <Plot
          ref={plotRef}
          data={[
            {
              y: currentData.linePlot.data,
              x: currentData.linePlot.time,
              name: 'Trace',
              type: 'scatter',
              mode: 'lines',
              marker: { color: '#1f77b4' },
            },
            {
              y: currentData.peaks.data,
              x: currentData.peaks.time,
              name: 'Peak values',
              type: 'scatter',
              mode: 'markers',
              marker: { size: 10, color: '#41337A' },
            },
            {
              y: currentData.valleys_start.data,
              x: currentData.valleys_start.time,
              name: 'Valley start',
              type: 'scatter',
              mode: 'markers',
              marker: { size: 10, color: '#76B041' },
            },
            {
              y: currentData.valleys_end.data,
              x: currentData.valleys_end.time,
              name: 'Valley end',
              type: 'scatter',
              mode: 'markers',
              marker: { size: 10, color: 'red' },
            },
            {
              y: selectedPoint.peak_data,
              x: selectedPoint.peak_time,
              name: 'Selected Point',
              type: 'scatter',
              mode: 'markers',
              marker: { size: 13, color: '#01FDF6' },
            },
            {
              y: tempCycle.valleyStart ? [tempCycle.valleyStart.y] : [],
              x: tempCycle.valleyStart ? [tempCycle.valleyStart.x] : [],
              name: 'Pending Valley Start',
              type: 'scatter',
              mode: 'markers',
              marker: {
                size: 12,
                color: 'green',
                symbol: 'diamond-open',
                line: { width: 2, color: 'green' },
              },
            },
            {
              y: tempCycle.peak ? [tempCycle.peak.y] : [],
              x: tempCycle.peak ? [tempCycle.peak.x] : [],
              name: 'Pending Peak',
              type: 'scatter',
              mode: 'markers',
              marker: {
                size: 12,
                color: 'purple',
                symbol: 'diamond-open',
                line: { width: 2, color: 'purple' },
              },
            },
          ]}
          onClick={handleClickOnPlot}
          config={{
            modeBarButtonsToRemove: [
              'select2d',
              'lasso2d',
            ],
            responsive: true,
            displaylogo: false,
            scrollZoom: true,
            toImageButtonOptions: {
              filename: tasks[selectedTaskIndex].fileName
                ? tasks[selectedTaskIndex].fileName + '_waveplot'
                : 'WavePlot',
            },
          }}
          layout={{
            plot_bgcolor: '#39393F',
            paper_bgcolor: '#333338',
            shapes,
            dragmode: 'pan',
            xaxis: {
              title: {
                text: 'Time [s]',
                standoff: 20,
                font: { color: '#f6f3f3ff' },
              },
              gridcolor: '#3F3F46',
              tickfont: { color: '#f3f4f6' },
              range: [startTime, endTime],
              fixedrange: false,
            },
            yaxis: {
              title: {
                text: 'Distance',
                standoff: 20,
                font: { color: '#f3f4f6' },
              },
              gridcolor: '#3F3F46',
              tickfont: { color: '#f3f4f6' },
              automargin: true,
              fixedrange: false,
            },
            height: 400,
            margin: { t: 10, r: 10, b: 40, l: 50 },
            legend: {
              x: 1,
              y: 1,
              xanchor: 'right',
              yanchor: 'top',
              bgcolor: 'rgba(51, 51, 56, 0.8)',
              font: {
                color: '#f3f4f6',
                size: 12,
                family: 'Arial, sans-serif',
              },
            },
            autosize: true,
            uirevision: uiRevision,
          }}
          style={{
            width: '100%',
            height: '400px',
            borderRadius: '1rem',
          }}
          useResizeHandler={true}
        />
      </div>
  
      {/* Buttons and Popups */}
      <div className="relative w-full max-w-5xl mt-4">
        <div className="flex justify-center gap-4">
          <Button
            variant="contained"
            onClick={() => {
              setTaskFlags({ addNew: true, remove: false });
              setAddPointName('valley_start');
              showPopUp('Please select the new valley start point.');
            }}
            sx={{
              bgcolor: 'primary.main',
              '&:hover': { bgcolor: 'primary.dark' },
              textTransform: 'none',
              fontWeight: 'bold',
              px: 3,
              py: 1,
            }}
          >
            Add Cycle
          </Button>
  
          <Button
            variant="contained"
            onClick={() => {
              setTaskFlags({ addNew: false, remove: true });
              showPopUp('Click on any point from the cycle you want to remove.');
            }}
            sx={{
              bgcolor: 'primary.main',
              '&:hover': { bgcolor: 'primary.dark' },
              textTransform: 'none',
              fontWeight: 'bold',
              px: 3,
              py: 1,
            }}
          >
            Remove Cycle
          </Button>
        </div>
  
        {popup.show && (
          <div
            className="absolute left-1/2 transform -translate-x-1/2 bg-white p-4 rounded-lg shadow-lg mt-2 w-3/4 max-w-xl z-50"
            style={{ top: '100%' }}
          >
            <div className="flex justify-between items-center">
              <span className="text-gray-800">{popup.msg}</span>
              <button
                className="font-bold ml-4 text-gray-600"
                onClick={cancelCurrentTask}
                aria-label="Close popup"
              >
                X
              </button>
            </div>
          </div>
        )}
  
        {alertPopup.show && (
          <div
            className="absolute left-1/2 transform -translate-x-1/2 bg-white p-4 rounded-lg shadow-lg mt-2 w-3/4 max-w-xl z-50"
            style={{ top: '100%' }}
          >
            <div className="flex justify-between items-center">
              <span className="text-gray-800">{alertPopup.msg}</span>
              <button
                className="font-bold ml-4 text-gray-600"
                onClick={cancelCurrentTask}
                aria-label="Close alert"
              >
                X
              </button>
            </div>
            <div className="flex justify-center gap-4 mt-4">
              <Button
                variant="contained"
                onClick={cancelCurrentTask}
                sx={{ textTransform: 'none', fontWeight: 'bold' }}
              >
                Cancel
              </Button>
              <Button
                variant="contained"
                onClick={continueAlert}
                sx={{ textTransform: 'none', fontWeight: 'bold' }}
              >
                Continue
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default WavePlotEditable;