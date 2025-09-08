import React, { useContext, useEffect} from 'react';
import { useNavigate } from 'react-router-dom';
import HeaderSection from './HeaderSection';
import VideoPlayer from '../../components/VideoPlayer/VideoPlayer';
import SubjectSelectionTab from './SubjectSelectionTab';
import SubjectsWaveForm from './SubjectsWaveForm';
import { VideoContext } from '../../contexts/VideoContext';

const SubjectResolution = () => {
  const {
    videoId,
    videoReady,
    setVideoReady,
    videoData,
    setVideoData,
    videoURL,
    setVideoURL,
    videoRef,
    fileName,
    setFileName,
    boundingBoxes,
    setBoundingBoxes,
    fps,
    setFPS,
    persons,
    setPersons,
    boxesReady,
    setBoxesReady,
    tasks,
    setTasks,
  } = useContext(VideoContext);

  const navigate = useNavigate();
  if(!videoId) {
    navigate("/")
  }

  const isSubject = id => persons.find(p => p.id === id)?.isSubject;

  const moveToNextScreen = () => {
    navigate('/tasks');
  };

  return (
    <div className="flex flex-col h-screen">
      <div className="flex flex-1 w-full h-full overflow-hidden">
        <div className="flex w-1/2 h-full">
          <VideoPlayer
            screen="subject_resolution"
            videoRef={videoRef}
            boundingBoxes={boundingBoxes}
            setBoundingBoxes={setBoundingBoxes}
            fps={fps}
            persons={persons}
            setVideoReady={setVideoReady}
            videoURL={videoURL}
            setVideoURL={setVideoURL}
            fileName={fileName}
            setFileName={setFileName}
            tasks={tasks}
            setTasks={setTasks}
          />
        </div>
        <div className="flex flex-col gap-2 w-1/2 h-full max-h-screen border-l border-l-zinc-600 overflow-y-auto bg-zinc-800">
          <HeaderSection
            title="Subject Selection"
            isVideoReady={videoReady}
            moveToNextScreen={moveToNextScreen}
            boundingBoxes={boundingBoxes}
            persons={persons}
            fps={fps}
            videoURL={videoURL}
            fileName={fileName}
          />
          <SubjectsWaveForm
            videoData={videoData}
            videoURL={videoURL}
            videoRef={videoRef}
            persons={persons}
            isVideoReady={videoReady}
            boxesReady={boxesReady}
          />
          <SubjectSelectionTab
            boundingBoxes={boundingBoxes}
            setBoundingBoxes={setBoundingBoxes}
            fps={fps}
            setFPS={setFPS}
            videoRef={videoRef}
            persons={persons}
            setPersons={setPersons}
            isVideoReady={videoReady}
            boxesReady={boxesReady}
            setBoxesReady={setBoxesReady}
          />
        </div>
      </div>
    </div>
  );
};

export default SubjectResolution;
