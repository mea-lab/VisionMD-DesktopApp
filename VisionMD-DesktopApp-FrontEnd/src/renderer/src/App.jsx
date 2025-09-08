// src/App.jsx
import SubjectResolution from './pages/SubjectResolution';
import HomePage from './pages/HomePage';
import { Routes, Route } from 'react-router-dom';
import TaskSelection from './pages/TaskSelection';
import TaskDetails from './pages/TaskDetails';
import { VideoProvider } from './contexts/VideoContext';


function App() {
  return (
    <VideoProvider>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/subjects" element={<SubjectResolution />} />
        <Route path="/tasks" element={<TaskSelection />} />
        <Route path="/taskdetails" element={<TaskDetails />} />
      </Routes>
    </VideoProvider>
  );
}

export default App;
