//src/pages/TaskDetails/HeaderSection.jsx
import NavigateBefore from '@mui/icons-material/NavigateBefore';
import { useNavigate } from 'react-router-dom';
import Typography from '@mui/material/Typography';
import Tooltip from '@mui/material/Tooltip';


const HeaderSection = ({ title }) => {
  const navigate = useNavigate();

  return (
    <header className="flex px-4 items-center justify-between bg-zinc-900 z-1 shadow-lg py-1 relative">
      <Typography className="text-gray-100">
        {title}
      </Typography>
        
      <span title="Go Back">
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
      </span>
    </header>
  );
};


export default HeaderSection;
