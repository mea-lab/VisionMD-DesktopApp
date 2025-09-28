// src/pages/TaskDetails/JSONUploadDialog.jsx
import { useState, useContext } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';
import { VideoContext } from '../../contexts/VideoContext';
const API_URL = import.meta.env.VITE_API_BASE_URL;

export default function JSONUploadDialog({
  dialogOpen,
  setDialogOpen,
  handleJSONUpload,
  selectedTask,
}) {
  const {
    videoId,
    videoRef,
    fps,
    tasks,
    boundingBoxes,
  } = useContext(VideoContext);

  const [fileError, setFileError] = useState('');
  const [jsonContent, setJSONContent] = useState(null);
  const [serverProcessing, setServerProcessing] = useState(false);

  const handleClose = () => {
    setDialogOpen(false);
    setFileError('');
  };

  const handleJSONProcess = () => {
    setFileError('');
    handleJSONUpload(true, jsonContent);
    setDialogOpen(false);
  };

  const handleAutoProcess = async () => {
    await fetchAnalysisDetails();
  };

  const handleFileChange = async event => {
    const file = event.target.files[0];
    if (file) {
      if (file.name.endsWith('.json') || file.name.endsWith('.parse')) {
        try {
          const content = await file.text();
          setJSONContent(JSON.parse(content));
          setFileError('');
        } catch (error) {
          setFileError('Error reading the file.');
        }
      } else {
        setFileError('Please select a valid JSON file.');
      }
    }
  };

  const fetchAnalysisDetails = async () => {
    const videoURL = videoRef.current.src;
    const content = await fetch(videoURL).then(r => r.blob());

    try {
      let uploadData = new FormData();
      let taskData = tasks[selectedTask];

      const chosenTaskBox = tasks.find(box => box.id === taskData.id);
      const taskBoxCords = {
        x: chosenTaskBox.x,
        y: chosenTaskBox.y,
        width: chosenTaskBox.box_width,
        height: chosenTaskBox.box_height,
      };

      const subjectBoundingBoxes = boundingBoxes
        .map(({ frameNumber, data }) => ({
          frameNumber,
          data: data.filter(item => item.Subject === true)
        }))
        
      const { start, end, name, data, ...otherTaskFields } = taskData;
      let jsonData = {
        boundingBox: taskBoxCords,
        task_name: taskData.name,
        start_time: taskData.start,
        end_time: taskData.end,
        fps: fps,
        subject_bounding_boxes: subjectBoundingBoxes,
        ...otherTaskFields,
      };
      
      jsonData = JSON.stringify(jsonData);
      uploadData.append('json_data', jsonData);        
      const sanitizedTaskName = taskData.name
        .replace(/[^a-zA-Z0-9]+/g, ' ')
        .split(' ')
        .filter(Boolean)
        .map(word => word.toLowerCase())
        .join('_');

      // Build the API URL with the sanitized task name.
      let apiURL = `${API_URL}/${sanitizedTaskName}/?id=${videoId}`;

      console.log("API URL Generated as:", apiURL);
      console.log("Upload data", JSON.parse(jsonData));

      setServerProcessing(true);
      const response = await fetch(apiURL, {
        method: 'POST',
        body: uploadData,
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log("Returned Data Content:", data)
        handleJSONUpload(true, data);
        setDialogOpen(false);
        setServerProcessing(false);
      } else {
        if (response.status === 404) {
          setServerProcessing(false);
          throw new Error('404 Error: API route for task is not found!');
        }
        setServerProcessing(false);
        const errorText = await response.text();
        throw new Error(`Server responded with ${response.status} error:\n ${errorText}`);
      }

    } catch (error) {
      setServerProcessing(false);
      console.error('Failed to fetch projects:', error);
      setFileError(error.message || 'Unknown error');
    }
  };

  return (
      <Dialog 
        open={dialogOpen} 
        onClose={handleClose}
        PaperProps={{
          sx: {
            backgroundColor: '#333338',
            borderRadius: 3,
          },
       }}
      >
        <DialogTitle className='text-gray-100'>
          <div className='flex flex-row w-full justify-between items-center'>
            Task Setup
            <IconButton onClick={handleClose}>
              <CloseIcon className='text-gray-100'/>
            </IconButton>
          </div>
        </DialogTitle>

        <DialogContent>
            {!serverProcessing && (
              <div>
                <div className='text-gray-100'>
                  Upload JSON containing the task analysis data or click on
                  analyze to analyze the task automatically.
                </div>

                <div className='flex w-full justify-center mt-8'>
                  <input
                    id="file-upload"
                    type="file"
                    accept=".json"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <label
                    htmlFor="file-upload"
                    className="cursor-pointer px-4 py-2
                              text-gray-100 bg-transparent rounded-md
                              border-2 border-zinc-600 border-dashed hover:bg-zinc-700"
                  >
                    Upload JSON File
                  </label>
                </div>
                <div className={fileError ? `mt-8` : ``}>
                  {fileError && <Typography color="error">{fileError}</Typography>}
                </div>
            </div>
            )}
            {serverProcessing && (
              <div
                className='flex flex-col w-full h-full justify-center items-center gap-10 text-gray-100'
              >
                <div>Server processing the request</div>
                <CircularProgress className='my-4' size={80} />
              </div>
            )}
        </DialogContent>

        <DialogActions>
          {!serverProcessing && (
          <div className='flex flex-row justify-between w-full p-2'>
            <button 
              className={`rounded-md p-1.5 ${(jsonContent === null || serverProcessing) ? "bg-transparent text-gray-500" : "bg-[#1976d2] hover:bg-[#1565c0] text-gray-100"}`}
              onClick={handleJSONProcess}
              disabled={jsonContent === null || serverProcessing}
            >
              Process with JSON
            </button>
            <button 
              className='rounded-md bg-[#1976d2] hover:bg-[#1565c0] p-1 px-2 text-gray-100' 
              onClick={() => {
                setFileError("");
                handleAutoProcess(); 
              }}
              disabled={serverProcessing}
            >
              Auto Process
            </button>
          </div>
          )}
        </DialogActions>
      </Dialog>
  );
}
