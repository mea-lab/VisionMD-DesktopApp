// src/pages/HomePage/projects.jsx
import { useEffect, useState, useRef, useContext, useCallback } from 'react';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import { Plus, Pencil } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { VideoContext } from "../../contexts/VideoContext";
import HighlightOffIcon from '@mui/icons-material/HighlightOff';
import CircularProgress from '@mui/material/CircularProgress';
import JSONUploadDialog from './JSONUploadDialog';

const BASE_URL = import.meta.env.VITE_BASE_URL;
dayjs.extend(relativeTime);

// Keep the previous cards visible when navigating back; refresh metadata below.
let cachedProjects = null;

const fetchVideos = async (url, signal) => {
  for (let attempt = 0; attempt < 6; attempt += 1) {
    try {
      const res = await fetch(url, { signal });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      if (!Array.isArray(data)) throw new Error('Invalid project list response');
      return data;
    } catch (error) {
      if (signal.aborted || attempt === 5) throw error;
      // Startup retries should not leave users waiting minutes between attempts.
      await new Promise(resolve => setTimeout(resolve, Math.min(500 * 2 ** attempt, 2000)));
      if (signal.aborted) throw error;
    }
  }
};


const uploadVideo = async (file) => {
  const form = new FormData();
  form.append('video', file);
  const res = await fetch(`${BASE_URL}/api/upload_video/`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Server responded with ${res.status} error:\n ${errorText}`);
  }
  return res.json();
}

const deleteVideo = async (id) => {
  const res = await fetch(`${BASE_URL}/api/delete_video/?id=${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    console.error('Delete API returned non-OK', res.status, await res.text());
    throw new Error('Delete failed');
  }
};

const renameVideo = async (id, videoName, fileType, setVideos) => {

  const request_body = {
    "video_name": `${videoName}.${fileType}`,
    "stem_name": `${videoName}`,
    "video_url": `/media/video_uploads/${id}/${videoName}.${fileType}`,
  }
  console.log("Request body", request_body)
  
  const res = await fetch(`${BASE_URL}/api/update_video_data/?id=${id}&file_name=metadata.json`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request_body),  
  });

  if (!res.ok) {
    console.error('Updating video name returned non-OK', res.status, await res.text());
    throw new Error('Updating video name failed');
  }

  const updatedTimestamp = new Date().toISOString();
  setVideos(vs =>
    vs.map(v => {
      if (v.metadata.id !== id) {
        return v;
      }

      return {
        ...v,
        metadata: {
          ...v.metadata,
          stem_name: videoName,
          video_name: `${videoName}.${v.metadata.file_type}`,
          video_url: `/media/video_uploads/${id}/${videoName}.${v.metadata.file_type}`,
          last_edited: updatedTimestamp,
        }
      };
    })
  )
}




const AddTile = ({ onClick }) => {
  return (
    <button
      onClick={onClick}
      className="
        w-full h-full
        rounded-lg flex
        p-4
        items-center justify-center
        border-2 border-dashed border-gray-500 
        hover:bg-gray-700 
        focus:outline-none focus:ring
      "
    >
      <div className="flex flex-col items-center">
        <Plus size={32}/>
        <span className="mt-2 text-sm">New Project</span>
      </div>
    </button>
  );
}





const VideoTile = ({ video, setVideos }) => {
  const [editing, setEditing] = useState(false);
  const [videoName, setVideoName] = useState(video.metadata.stem_name);
  const navigate = useNavigate();
  const snapshotInputRef = useRef();
  const {
    setVideoId,
  } = useContext(VideoContext);

  const onVideoNameChange = (newStemName) => {
    setVideoName(newStemName);
  }

  const openVideoProject = async () => {
    setVideoId(video.metadata.id)
    navigate("/subjects");
  }

  const handleDeleteClick = async () => {
    console.log("Running delete")
    try {
      await deleteVideo(video.metadata.id);
      setVideos(vs => vs.filter(v => v.metadata.id !== video.metadata.id));
    } catch (err) {
      console.error('Video delete failed:', err);
    }
  };

  const importSnapshot = async event => {
    const file = event.target.files?.[0];
    event.target.value = null;
    if (!file) return;
    try {
      const snapshot = JSON.parse(await file.text());
      const response = await fetch(`${BASE_URL}/api/import_project_snapshot/?id=${video.metadata.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(snapshot),
      });
      if (!response.ok) throw new Error(await response.text());
      setVideoId(video.metadata.id);
      navigate('/subjects');
    } catch (error) {
      window.alert(`Could not import project JSON: ${error.message || error}`);
    }
  };

  const downloadSnapshot = async () => {
    try {
      const response = await fetch(`${BASE_URL}/api/get_video_data/?id=${video.metadata.id}`);
      if (!response.ok) throw new Error(await response.text());
      const project = await response.json();
      const snapshot = {
        format: 'visionmd-project',
        version: 1,
        video: {
          name: video.metadata.video_name,
          fps: video.metadata.fps,
          frame_count: video.metadata.frame_count,
          duration: video.metadata.source_duration,
          rotation: video.metadata.rotation,
        },
        data: {
          fps: project.metadata?.fps ?? video.metadata.fps,
          persons: project.persons ?? [],
          boundingBoxes: project.boundingBoxes ?? [],
          tasks: project.tasks ?? [],
        },
      };
      const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: 'application/json' });
      const href = URL.createObjectURL(blob);
      const link = Object.assign(document.createElement('a'), {
        href,
        download: `${video.metadata.stem_name}_visionmd_project.json`,
      });
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(href);
    } catch (error) {
      window.alert(`Could not create project JSON: ${error.message || error}`);
    }
  };

  return (
    <div 
      className="relative group rounded-lg hover:bg-gray-700 bg-surfaceElevated p-4 flex flex-col overflow-visible h-full"
    >
      <button
        onClick={handleDeleteClick}
        className="absolute z-10 top-2 right-2 opacity-0 group-hover:opacity-100 bg-gray-700 rounded-full text-white inline-flex items-center justify-center"
      >
        <HighlightOffIcon className="text-white hover:text-gray-400 transition-colors duration-200" fontSize="small" />
      </button>
      
      <img
        src={`${BASE_URL}${video.metadata.thumbnail_url}?t=${video.metadata.last_edited}`}
        className="rounded-lg w-full aspect-video object-contain cursor-pointer bg-zinc-900"
        loading="lazy"
        decoding="async"
        alt={`Thumbnail for ${video.metadata.video_name}`}
        onClick={() => openVideoProject()}
      />

      <div className="flex items-center mt-2">
        {editing ? (
          <div className='flex flex-row w-full items-start justify-items-start'>
            <input
              className="p-0 bg-transparent border-b border-gray-400 text-sm focus:outline-none"
              value={videoName}
              onBlur={() => setEditing(false)}
              onChange={e => onVideoNameChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.target.blur();
                  renameVideo(video.metadata.id, videoName, video.metadata.file_type, setVideos);
                }
              }}
              autoFocus
            />
          </div>
        ) : (
          <h3 className="flex-1 text-sm truncate" title={videoName}>{videoName}.{video.metadata.file_type}</h3>
        )}
        <button 
          onClick={() => {
            setEditing(true)}
          }
          aria-label="Edit title"
          className="p-1 hover:text-gray-400"
        >
          <Pencil size={14}/>
        </button>
      </div>
      <p className="text-xs text-gray-400">Last edited {dayjs(video.metadata.last_edited).fromNow()}</p>
      <input ref={snapshotInputRef} type="file" accept="application/json,.json" className="hidden" onChange={importSnapshot} />
      <div className="mt-3 flex gap-2 text-xs">
        <button
          onClick={downloadSnapshot}
          className="rounded border border-zinc-500 px-2 py-1 text-blue-200 transition-colors hover:bg-zinc-700 hover:text-white hover:font-semibold"
        >
          Download project JSON
        </button>
        <button
          onClick={() => snapshotInputRef.current?.click()}
          className="rounded border border-zinc-500 px-2 py-1 text-blue-200 transition-colors hover:bg-zinc-700 hover:text-white hover:font-semibold"
        >
          Load project JSON
        </button>
      </div>
    </div>
  );
}





export default function Projects() {
  const [videos, updateVideos] = useState(() => cachedProjects);
  const projectMutations = useRef(0);
  const setVideos = useCallback(update => {
    projectMutations.current += 1;
    updateVideos(update);
  }, []);
  const [loading, setLoading] = useState(() => cachedProjects === null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const fileInputRef = useRef();
  const [loadError, setLoadError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const mutationVersion = projectMutations.current;
    setLoadError(null);
    fetchVideos(`${BASE_URL}/api/get_video_metadata/`, controller.signal)
      .then(data => {
        if (!controller.signal.aborted && projectMutations.current === mutationVersion) {
          updateVideos(data);
        }
      })
      .catch(error => {
        if (!controller.signal.aborted) setLoadError(error.message || String(error));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [reloadKey]);

  useEffect(() => {
    if (videos !== null) cachedProjects = videos;
  }, [videos]);

  useEffect(() => {
    if (videos && videos.length > 0) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [videos]);

  const handleAddClick = () => fileInputRef.current.click();

  useEffect(() => {
    const openNewProject = () => fileInputRef.current?.click();
    window.addEventListener('visionmd:shortcut:new-project', openNewProject);
    return () => window.removeEventListener('visionmd:shortcut:new-project', openNewProject);
  }, []);

  const handleFiles = async e => {
    setDialogOpen(true);
    const file = e.target.files[0];

    if (!file) return;
    try {
      const response_metadata = await uploadVideo(file);
      setVideos(v => [response_metadata, ...(v ?? [])]);
      setDialogOpen(false);
    } catch(error) {
      setUploadError(error.message || String(error));
      console.error('Video upload failed:', error);
    } finally {
      e.target.value = null; 
    }
  };
  return (
    <div>
      {loadError && (
        <div role="alert" className="mb-4 rounded border border-red-400 p-3">
          Could not load projects: {loadError}.
          <button className="ml-3 underline" onClick={() => {
            setLoading(videos === null);
            setReloadKey(value => value + 1);
          }}>Retry</button>
        </div>
      )}
      {loading && !videos && (
        <div className="flex items-center justify-center h-screen">
          <CircularProgress className='my-4' size={64} />
        </div>
      )}
      {/* Hidden input for video uploading*/}
      <input
        ref={fileInputRef}
        type="file"
        accept="video/*"
        className="hidden"
        onChange={handleFiles}
      />

      {/* Grid for video tiles and add project tile */}
      <div className="grid gap-8" style={{ gridTemplateColumns: 'repeat(auto-fill,minmax(220px,1fr))' }}>
        {videos && (
          <>
            {/* Add project tile */}
            <div key={"add"} style={{ width: '100%', aspectRatio: '4 / 3' }}>
              <AddTile className="w-full h-full" onClick={handleAddClick} />
            </div>
            
            {/* All video tiles */}
            {videos.map((video) => (
              <div key={video.metadata.id} style={{ width: '100%', minHeight: 220 }}>
                <VideoTile className="w-full h-full" video={video} setVideos={setVideos}/>
              </div>
            ))}
          </>
        )}
      </div>
      {dialogOpen && (
        <JSONUploadDialog
          dialogOpen={dialogOpen}
          setDialogOpen={setDialogOpen}
          uploadError={uploadError}
          setUploadError={setUploadError}
        />
      )}
    </div>
  );
}
