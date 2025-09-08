import React, { useEffect, useState } from 'react';
import PlayCircleOutline from '@mui/icons-material/PlayCircleOutline';
import Button from '@mui/material/Button';
import JSONUploadDialog from './SubjectJSONUploadDialog';


const PersonRow = ({ person, onPlay, onToggleSubject }) => (
  <li className='flex items-center justify-between p-2 border border-zinc-500 rounded-lg bg-zinc-600 hover:bg-zinc-500 text-gray-100 transition-colors duration-150'>
    <div className='flex flex-row justify-between w-full'>
      <div className="flex items-center">
        <PlayCircleOutline onClick={() => onPlay(person.timestamp)} className="cursor-pointer" />
        <span className="ml-2 font-medium">{person.name}</span>
        <span className="ml-4 text-sm">{person.timestamp}</span>
      </div>
      <button
        onClick={() => onToggleSubject(person)}
        className={`px-4 py-1 rounded text-xs font-semibold shadow-sm transition-colors duration-150 ${
          person.isSubject ? 'bg-red-500 hover:bg-red-600 text-gray-100' : 'bg-emerald-600 hover:bg-emerald-700 text-gray-100'
        }`}
      >
        {person.isSubject ? 'Remove as Subject' : 'Mark as Subject'}
      </button>
    </div>
  </li>
);

const SubjectSelectionTab = ({
  videoRef,
  setFPS,
  fps,
  setBoundingBoxes,
  boundingBoxes,
  persons,
  setPersons,
  isVideoReady,
  setBoxesReady,
  boxesReady,
}) => {
  const [openJsonUpload, setOpenJsonUpload] = useState(false);

  const convertFrameNumberToTimestamp = frameNumber =>
    (frameNumber / fps).toFixed(2);

  useEffect(() => {
    if (persons.length !== 0) return;

    const firstOccurrenceMap = new Map();
    if (Array.isArray(boundingBoxes)) {
      boundingBoxes.forEach(frameData => {
        frameData.data.forEach(p => {
          if (!firstOccurrenceMap.has(p.id)) {
            firstOccurrenceMap.set(p.id, frameData.frameNumber);
          }
        });
      });
    }

    const personArray = Array.from(firstOccurrenceMap, ([id, frameNumber]) => ({
      id,
      name: `Person ${id}`,
      frameNumber,
      timestamp: convertFrameNumberToTimestamp(frameNumber),
      isSubject: false,
    }));

    setPersons(personArray);
  }, [boundingBoxes, persons.length, fps, setPersons]);

  useEffect(() => {
    if (persons.length === 1 && !persons[0].isSubject) {
      setPersons(persons.map(person => ({ ...person, isSubject: true })));
      setBoundingBoxes(prev =>
        prev.map(frame => ({
          ...frame,
          data: frame.data.map(box =>
            box.id === persons[0].id
              ? { ...box, Subject: true }
              : box
          )
        }))
      );
    }
  }, [persons, setPersons]);

  const handlePlay = timestamp => {
    if (videoRef?.current && videoRef.current.readyState === 4) {
      videoRef.current.currentTime = parseFloat(timestamp) + 0.25;
    }
  };

  const handleToggleSubject = selectedPerson => {
    setPersons(
      persons.map(person =>
        person.id === selectedPerson.id
          ? { ...person, isSubject: !person.isSubject }
          : person
      )
    );

    setBoundingBoxes(prev =>
      prev.map(frame => ({
        ...frame,
        data: frame.data.map(box =>
          box.id === selectedPerson.id
            ? { ...box, Subject: !box.Subject }
            : box
        )
      }))
    );
  };

  const jsonFileHandle = (jsonFileUploaded, jsonContent) => {
    if (jsonFileUploaded) {
      setBoundingBoxes(jsonContent.boundingBoxes);
      if (jsonContent.persons) {
        setPersons(jsonContent.persons);
      }
      setBoxesReady(true);
    }
  };

  if (!isVideoReady) {
    return (
      <div className="w-full h-[65vh] flex items-center justify-center">
        <div className="bg-transparent border-2 border-zinc-600 p-4 rounded-lg shadow-md">
          <p className="text-center text-lg text-gray-100">Waiting for video to load...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen p-2">
      <div className="h-full overflow-y-auto p-4 rounded-lg bg-[#333338] shadow-inner">
        {!boxesReady ? (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-gray-100">
            <div>Process the video to start subject selection</div>
            <Button 
            variant="contained"
            onClick={() => setOpenJsonUpload(true)}
            sx={{
              bgcolor: 'primary.main',
              '&:hover': { bgcolor: 'primary.dark' },
              textTransform: 'none',
              px: 3,
              py: 1,
              fontSize: '1rem'
            }}
          >
            Process Video
          </Button>
            <JSONUploadDialog
              dialogOpen={openJsonUpload}
              setDialogOpen={setOpenJsonUpload}
              handleJSONUpload={jsonFileHandle}
              videoRef={videoRef}
            />
          </div>
        ) : (
          <>
            <div className="flex flex-col border-b-2 py-2 text-gray-100 border-zinc-500">
              Subjects
            </div>
            <ul className="py-2 space-y-2">
              {persons.map((subject, index) => (
                <PersonRow
                  key={subject.id || index}
                  person={subject}
                  onPlay={handlePlay}
                  onToggleSubject={handleToggleSubject}
                />
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
};

export default SubjectSelectionTab;
