import Download from '@mui/icons-material/Download';
import NavigateNext from '@mui/icons-material/NavigateNext';
import NavigateBefore from '@mui/icons-material/NavigateBefore';
import Home from '@mui/icons-material/Home'
import Typography from '@mui/material/Typography';
import Tooltip from '@mui/material/Tooltip';
import { useNavigate } from 'react-router-dom';


const HeaderSection = ({
  title,
  boundingBoxes,
  persons,
  fileName,
  fps,
  frameCount,
  moveToNextScreen,
  tasks,
}) => {
  const navigate = useNavigate();
  const notProceed = !(tasks.length > 0 && tasks.every(t => t.name != "Region"));

  const downloadConfig = () => {
    const fileData = {
      format: 'visionmd-project',
      version: 1,
      video: { name: fileName, fps, frame_count: frameCount },
      data: { fps, persons, boundingBoxes, tasks },
    };
    
    const json = JSON.stringify(fileData);
    const blob = new Blob([json], { type: 'application/json' });
    const href = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = href;
    link.download = fileName.replace(/\.[^/.]+$/, '') + '_visionmd_project.json';
    document.body.appendChild(link);
    link.click();
    
    document.body.removeChild(link);
    URL.revokeObjectURL(href);
  };
  
  return (
    <div className="flex px-4 items-center justify-between bg-zinc-900 z-1 shadow-lg py-1 relative">
      <div className="flex gap-3 items-center">
        <Tooltip arrow title="Home">
          <Home
            onClick={() => navigate('/')}
            className="cursor-pointer text-white hover:text-gray-300"
            fontSize="small"
          />
        </Tooltip>
        <Typography className="text-gray-100" fontWeight="500">
          {title}
        </Typography>
      </div>

      <div className="flex gap-3 items-center">
        <Tooltip arrow title="Go Back">
          <NavigateBefore
            data-shortcut-action="back"
            onClick={() => navigate('/subjects')}
            className="cursor-pointer text-white hover:text-gray-300"
            fontSize="medium"
          />
        </Tooltip>

        <Tooltip arrow title="Download complete project">
          <Download
            onClick={notProceed ? undefined : downloadConfig}
            className={`cursor-pointer ${notProceed ? 'text-gray-500 cursor-not-allowed' : 'text-white hover:text-gray-300'}`}
            fontSize="small"
          />
        </Tooltip>
        
        <Tooltip arrow title="Go Forward">
          <NavigateNext
            data-shortcut-action="forward"
            onClick={notProceed ? undefined : moveToNextScreen}
            className={`cursor-pointer ${notProceed ? 'text-gray-500 cursor-not-allowed' : 'text-white hover:text-gray-300'}`}
            fontSize="medium"
          />
        </Tooltip>
      </div>
    </div>
  );
};

export default HeaderSection;
