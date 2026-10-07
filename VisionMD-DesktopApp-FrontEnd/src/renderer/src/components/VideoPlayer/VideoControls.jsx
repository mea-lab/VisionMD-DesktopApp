import { useEffect } from 'react';
import Pause from '@mui/icons-material/Pause';
import PlayArrow from '@mui/icons-material/PlayArrow';
import Tooltip from '@mui/material/Tooltip';

const VideoControls = ({ videoRef, isPlaying, fps }) => {

  const checkVideoLoaded = (minimumReadyState = 4) => {
    const video = videoRef.current;
    if (!video) return false;
    if (video.error) {
      console.error('Video error:', video.error.message);
      return false;
    }
    if (!video.src && !video.currentSrc) {
      console.error('No video source is set.');
      return false;
    }
    return video.readyState >= minimumReadyState;
  };

  const playOrPause = () => {
    // At the end, readyState can fall below HAVE_ENOUGH_DATA. The current
    // frame is sufficient to seek back and request playback again.
    if (!checkVideoLoaded(2)) return;
    const video = videoRef.current;
    const atEnd = video.ended || (
      Number.isFinite(video.duration) && video.duration > 0 &&
      video.currentTime >= video.duration
    );
    if (atEnd) video.currentTime = 0;
    if (video.paused || atEnd) {
      video.play().catch(error => console.warn('Could not start video playback:', error));
    } else video.pause();
  };

  const changeVideoTime = (offset) => {
    if (checkVideoLoaded()) {
      videoRef.current.currentTime += offset;
    }
  };

  const changeVideoFrame = (frameOffset) => {
    if (checkVideoLoaded()) {
      const timeOffset = frameOffset / fps;
      changeVideoTime(timeOffset);
    }
  };

  const handleKey = (event) => {
    if (!videoRef.current) return;
    switch (event.key) {
      case 'ArrowRight':
        changeVideoFrame(1);
        event.preventDefault();
        break;
      case 'ArrowLeft':
        changeVideoFrame(-1);
        event.preventDefault();
        break;
      case 'ArrowUp':
        changeVideoFrame(5);
        event.preventDefault();
        break;
      case 'ArrowDown':
        changeVideoFrame(-5);
        event.preventDefault();
        break;
      case ' ':
        playOrPause();
        event.preventDefault();
        break;
      default:
        break;
    }
  };

  useEffect(() => {
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [fps, videoRef]);

  return (
    <div className="flex gap-4 text-xl justify-center items-center bg-zinc-700 backdrop-blur-md rounded-2xl px-4 py-2 text-gray-100">
      <Tooltip arrow title="Down Arrow">
        <button onClick={() => changeVideoFrame(-5)}> -5 </button>
      </Tooltip>
      <Tooltip arrow title="Left Arrow">
        <button onClick={() => changeVideoFrame(-1)}> -1 </button>
      </Tooltip>
      <Tooltip arrow title="Space Bar">
        {isPlaying ? (
          <Pause className="cursor-pointer" onClick={playOrPause} />
        ) : (
          <PlayArrow className="cursor-pointer" onClick={playOrPause} />
        )}
      </Tooltip>
      <Tooltip arrow title="Right Arrow">
        <button onClick={() => changeVideoFrame(1)}> +1 </button>
      </Tooltip>
      <Tooltip arrow title="Up Arrow">
        <button onClick={() => changeVideoFrame(5)}> +5 </button>
      </Tooltip>
    </div>
  );
};

export default VideoControls;
