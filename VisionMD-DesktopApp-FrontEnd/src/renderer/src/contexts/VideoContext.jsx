// src/contexts/VideoContext.jsx
import React, { createContext, useState, useEffect, useRef } from 'react';
export const VideoContext = createContext();
import { useAutoSave } from '@/hooks/useAutoSave';
import { isEqual } from "lodash";


const API_URL = import.meta.env.VITE_API_BASE_URL;
const BASE_URL = import.meta.env.VITE_BASE_URL


export const VideoProvider = ({ children }) => {
    const [videoId, setVideoId] = useState(null);
    const [videoData, setVideoData] = useState(null);
    const [videoURL, setVideoURL] = useState("");
    const [fileName, setFileName] = useState("");
    const [fps, setFPS] = useState(null);

    const [persons, setPersons] = useState([]);
    const [boundingBoxes, setBoundingBoxes] = useState([]);
    const [tasks, setTasks] = useState([]);

    const [videoReady, setVideoReady] = useState(false);
    const [boxesReady, setBoxesReady] = useState(false);
    const [tasksReady, setTasksReady] = useState(false);

    const videoRef = useRef(null);
    
    // Auto save hook on video context enables auto saving on route changes and refreshes
    useAutoSave(
        videoId,
        persons,
        boundingBoxes,
        tasks,
    )

    // useEffect for getting video information if video id is updated
    useEffect(() => {
        const prepareVideoData = async (videoId) => {
            try {
                // Grabbing metadata and video from backend
                console.log("Video ID changed", videoId)

                const data_response = await fetch(`${API_URL}/get_video_data/?id=${videoId}`);
                if (!data_response.ok) throw new Error('Failed to fetch metadata');
                const data = await data_response.json();

                const metadata = data.metadata;
                
                // Setting metadata and info 
                setVideoURL(`${BASE_URL}${metadata.video_url}`);
                setFileName(metadata.video_name);
                setFPS(metadata.fps);

                // Setting potential data that was stored previously (bounding boxes, tasks, landmarks, signals)
                if (data.persons) {
                setPersons(prev => isEqual(prev, data.persons) ? prev : data.persons);
                }
                if (data.boundingBoxes) {
                setBoundingBoxes(prev => isEqual(prev, data.boundingBoxes) ? prev : data.boundingBoxes);
                setBoxesReady(true);
                }
                if (data.tasks) {
                setTasks(prev => isEqual(prev, data.tasks) ? prev : data.tasks);
                setTasksReady(true);
                }
            } catch (error) {
                console.error('Error fetching video data on video project opening:\n', error);
            }
        }

        if (!videoId) return;
        
        //Reset video information first, then get video information we might have stored
        setVideoData(null);
        setVideoURL("");
        setFileName("");
        setFPS(null);
        setPersons([]);
        setBoundingBoxes([]);
        setTasks([]);
        setVideoReady(false);
        setBoxesReady(false);
        setTasksReady(false);

        prepareVideoData(videoId);

        return () => {
            console.log("Unmounting video context...")
            setFileName("");
            setVideoURL("");
            setVideoReady(false);
        }
    },[videoId])

    return (
        <VideoContext.Provider
            value={{
                videoId,
                setVideoId,
                videoRef,
                videoData,
                setVideoData,
                videoURL,
                setVideoURL,
                videoReady,
                setVideoReady,
                fileName,
                setFileName,
                fps,
                setFPS,
                boundingBoxes,
                setBoundingBoxes,
                tasks,
                setTasks,
                tasksReady,
                setTasksReady,
                persons,
                setPersons,
                boxesReady,
                setBoxesReady,
            }}
        >
            {children}
        </VideoContext.Provider>
    );
};
