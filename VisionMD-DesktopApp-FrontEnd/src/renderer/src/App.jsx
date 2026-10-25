// src/App.jsx
import SubjectResolution from './pages/SubjectResolution';
import HomePage from './pages/HomePage';
import { Routes, Route, useLocation, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import TaskSelection from './pages/TaskSelection';
import TaskDetails from './pages/TaskDetails';
import { VideoProvider } from './contexts/VideoContext';


function App() {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const clickAction = action => {
      const control = document.querySelector(
        `[data-shortcut-action="${action}"]:not([disabled])`,
      );
      if (control) {
        control.click();
        return true;
      }
      window.dispatchEvent(new CustomEvent(`visionmd:shortcut:${action}`));
      return false;
    };

    const onKeyDown = event => {
      if (!event.ctrlKey || event.altKey || event.metaKey) return;
      const target = event.target;
      if (target?.matches?.('input, textarea, select, [contenteditable="true"]')) return;

      const key = event.key.toLowerCase();
      const actions = {
        n: 'new-project', b: 'back', f: 'forward', p: 'process',
        u: 'auto-process', h: 'home', a: 'analyze', l: 'analyze-all',
      };
      const action = actions[key];
      if (!action) return;
      event.preventDefault();

      if (action === 'home') {
        navigate('/');
      } else if (action === 'new-project') {
        if (location.pathname !== '/') navigate('/');
        window.setTimeout(() => window.dispatchEvent(
          new CustomEvent('visionmd:shortcut:new-project')), 150);
      } else if (action === 'auto-process') {
        if (!clickAction('auto-process')) {
          clickAction(location.pathname === '/taskdetails' ? 'analyze' : 'process');
          window.setTimeout(() => clickAction('auto-process'), 50);
        }
      } else {
        clickAction(action);
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [location.pathname, navigate]);

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
