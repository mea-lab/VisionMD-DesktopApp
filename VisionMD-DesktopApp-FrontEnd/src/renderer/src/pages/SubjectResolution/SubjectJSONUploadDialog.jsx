import { useState, useContext } from 'react';

import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import CircularProgress from '@mui/material/CircularProgress';
import Input from '@mui/material/Input';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';

import { VideoContext } from '@/contexts/VideoContext';

export default function JSONUploadDialog({ dialogOpen, setDialogOpen, handleJSONUpload }) {
  const [fileName, setFileName] = useState('');
  const [fileError, setFileError] = useState('');
  const [jsonContent, setJSONContent] = useState(null);
  const [serverProcessing, setServerProcessing] = useState(false);

  const {
    videoRef,
    videoId,
  } = useContext(VideoContext)

  const handleClose = () => {
    setDialogOpen(false);
    setFileName('');
    setFileError('');
  };

  const handleJSONProcess = () => {
    setFileName('');
    setFileError('');
    handleJSONUpload(true, jsonContent);
    setDialogOpen(false);
  };

  const getVideoData = async () => {
    setServerProcessing(true);
    const videoURL = videoRef.current.src;
    const blob = await fetch(videoURL).then(r => r.blob());
    await fetchBoundingBoxes(blob);
  };

  const fetchBoundingBoxes = async (content) => {
    try {
      const response = await fetch(`http://localhost:8000/api/get_bounding_boxes/?id=${videoId}`, {
        method: 'GET',
      });
      if (!response.ok) {
        throw new Error('Server responded with an error!');
      }
      const data = await response.json();
      console.log("Returned subject resolution data",data)
      handleJSONUpload(true, data);
      setDialogOpen(false);
    } catch (error) {
      console.error('Failed to fetch projects:', error);
      setFileError(error.message);
    } finally {
      setServerProcessing(false);
    }
  };

  const handleAutoProcess = async () => {
    await getVideoData();
  };

  const validateJson = data => {
    try {
      if (!('fps' in data)) {
        throw new Error('fps field is missing.');
      }
      if (typeof data.fps !== 'number') {
        throw new Error('fps should be a number.');
      }
      if (!('boundingBoxes' in data)) {
        throw new Error('boundingBoxes field is missing.');
      }
      if (!Array.isArray(data.boundingBoxes)) {
        throw new Error('boundingBoxes should be an array.');
      }
      data.boundingBoxes.forEach(box => {
        if (!('frameNumber' in box)) {
          throw new Error('frameNumber field in boundingBoxes is missing.');
        }
        if (typeof box.frameNumber !== 'number') {
          throw new Error('frameNumber in boundingBoxes should be a number.');
        }
        if (!('data' in box)) {
          throw new Error('data field in boundingBoxes is missing.');
        }
        if (!Array.isArray(box.data)) {
          throw new Error('data in boundingBoxes should be an array.');
        }
        box.data.forEach(item => {
          if (!('id' in item)) {
            throw new Error('id field in boundingBoxes data is missing.');
          }
          ['x', 'y', 'width', 'height'].forEach(prop => {
            if (!(prop in item)) {
              throw new Error(`${prop} field in boundingBoxes data is missing.`);
            }
            if (typeof item[prop] !== 'number') {
              throw new Error(`${prop} in boundingBoxes data should be a number.`);
            }
          });
        });
      });
      return true;
    } catch (error) {
      setFileError(error.message);
      return false;
    }
  };

  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    if (!file.name.endsWith('.json')) {
      setFileError('Please select a valid JSON file.');
      return;
    }
    try {
      const content = await file.text();
      const parsed = JSON.parse(content);
      if (validateJson(parsed)) {
        setJSONContent(parsed);
        setFileName(file.name);
        setFileError('');
      }
    } catch (error) {
      setFileError('Error reading the file.');
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
          minWidth: 400,
        },
      }}
    >
      <DialogTitle className='text-gray-100'>
        <div className='flex flex-row w-full justify-between'>
          Video Parser
          <IconButton onClick={handleClose}>
            <CloseIcon className='text-gray-100'/>
          </IconButton>
        </div>
      </DialogTitle>

      <DialogContent>
        {!serverProcessing ? (
          <div>
            <p className="text-gray-100">
              Upload JSON manually containing the bounding boxes for the video or click on auto-parse to let the server handle it.
            </p>
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
        ) : (
          <div className="flex flex-col w-full h-full justify-center items-center gap-10">
            <div className='text-gray-100'>Server processing the request</div>
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
            <button className='rounded-md bg-[#1976d2] hover:bg-[#1565c0] p-1.5 text-gray-100' onClick={handleAutoProcess} disabled={serverProcessing}>
              Auto-Process
            </button>
          </div>
        )}
      </DialogActions>
    </Dialog>
  );
}
