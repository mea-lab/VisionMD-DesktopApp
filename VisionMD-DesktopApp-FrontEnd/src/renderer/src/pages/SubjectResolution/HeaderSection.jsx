import Typography from '@mui/material/Typography';
import Download from '@mui/icons-material/Download';
import NavigateNext from '@mui/icons-material/NavigateNext';
import NavigateBefore from '@mui/icons-material/NavigateBefore';
import { useNavigate } from 'react-router-dom';
import Tooltip from '@mui/material/Tooltip';

const HeaderSection = ({
  title,
  boundingBoxes,
  persons,
  fps,
  moveToNextScreen,
  fileName,
}) => {
  const navigate = useNavigate();

  const downloadConfig = () => {
    const data = { fps, boundingBoxes, persons };
    const json = JSON.stringify(data);
    const blob = new Blob([json], { type: 'application/json' });
    const href = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = href;
    link.download = fileName.replace(/\.[^/.]+$/, '') + '_subject_data.json';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(href);
  };

  return (
    <div className="flex px-4 items-center justify-between bg-zinc-900 z-1 shadow-lg py-1 relative">
      <Typography className="text-gray-100" fontWeight="500">
        {title}
      </Typography>

      <div className="flex gap-3 items-center">
        <Tooltip
          arrow
          title="Go Back"
        >
        <NavigateBefore
          onClick={() => navigate('/')}
          className="cursor-pointer text-white hover:text-gray-300"
          fontSize="medium"
        />
        </Tooltip>

        <Tooltip
          arrow
          title="Download Config"
        >
        <Download
          onClick={boundingBoxes?.length === 0 ? undefined : downloadConfig}
          className={`cursor-pointer ${boundingBoxes.length === 0 ? 'text-gray-500 cursor-not-allowed' : 'text-white hover:text-gray-300'}`}
          fontSize="small"
        />
        </Tooltip>
      
        <Tooltip
          arrow
          title="Go Forward"
        >
        <NavigateNext
          onClick={boundingBoxes?.length === 0 ? undefined : moveToNextScreen}
          className={`cursor-pointer ${boundingBoxes.length === 0 ? 'text-gray-500 cursor-not-allowed' : 'text-white hover:text-gray-300'}`}
          fontSize="medium"
        />
        </Tooltip>
      </div>
    </div>
  );
};

export default HeaderSection;