//src/pages/TaskDetails/HeaderSection.jsx
import NavigateBefore from '@mui/icons-material/NavigateBefore';
import Home from '@mui/icons-material/Home'
import { useNavigate } from 'react-router-dom';
import Typography from '@mui/material/Typography';
import Tooltip from '@mui/material/Tooltip';


const HeaderSection = ({ title }) => {
  const navigate = useNavigate();

  return (
    <header className="flex px-4 items-center justify-between bg-zinc-900 z-1 shadow-lg py-1 relative">
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
        
        <Tooltip
          arrow
          title='Go back'
        >
          <NavigateBefore
            onClick={() => navigate('/tasks')}
            className="cursor-pointer text-white hover:text-gray-300"
            fontSize="medium"
          />
        </Tooltip>
    </header>
  );
};


export default HeaderSection;
