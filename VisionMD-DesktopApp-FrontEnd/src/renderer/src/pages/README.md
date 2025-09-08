# Pages Directory

This directory contains the main UI views and logical sections of the application. Each subdirectory represents a distinct step in the video analysis workflow.

## Architecture Overview

The application follows a component-based architecture with each page handling a specific phase of video processing:

```
pages/
├── HomePage/            # Entry point for video upload
├── SubjectResolution/   # Subject identification and bounding box creation
├── TaskSelection/       # Task definition and timeline management
└── TaskDetails/         # Analysis visualization and data editing
```

## Core Pages

### HomePage
- **Purpose**: Application entry point handling user uploads
- **Key Components**: 
    - VideoUploadForm - manages file selection and validation
    - FormatSelector - controls output format settings

### SubjectResolution
- **Purpose**: Subject identification and bounding box creation
- **Key Components**:
    - InteractiveOverlays - manages overlay creation and manipulation
    - BoundingBoxManager - handles box state and persistence
- **Technical Details**:
    - Uses canvas-based drawing with custom resize handlers
    - Implements drag-and-drop functionality via mouse event handlers
    - Stores box coordinates as normalized values (0-1) for resolution independence

### TaskDetails
- **Purpose**: Detailed task analysis and data visualization
- **Key Components**: 
    - PlotWidget - container for visualization components
    - WavePlotEditable - interactive waveform visualization
    - ScatterPlot - visualization for multi-dimensional metrics
- **Technical Details**:
    - Integrates with video timeline via currentTime reference
    - Uses frame-based indexing for landmark rendering
    - Supports CSV data export for external analysis

### TaskSelection
- **Purpose**: Task definition and time segment marking
- **Key Components**:
    - TaskSelectionTab - handles task type selection and parameters
    - TasksWaveForm - timeline visualization with task markers
- **Technical Details**:
    - Implements WaveSurfer.js for audio visualization
    - Uses region markers to define task boundaries
    - Supports JSON schema for batch task import/export

## State Management

- **VideoContext**: Central state provider for video-related data
    - Maintains video metadata, task definitions, and bounding box information
    - Shared across all pages to maintain consistent application state

- **Data Flow**:
    1. Video loaded in HomePage → videoRef and metadata stored in context
    2. Subject boxes defined in SubjectResolution → stored in boundingBoxes array
    3. Tasks defined in TaskSelection → stored in taskBoxes and tasks arrays
    4. Analysis performed in TaskDetails → updates task.data objects

## Development Guidelines

### Adding New Tasks
1. Add task type to the options list in `TaskList.jsx`
2. Implement corresponding visualization in TaskDetails if needed
3. Update backend processing endpoints to handle the new task type

### Extending Visualization Components
- Visualization components use a common props interface including:
    - `selectedTaskIndex`: Current task being visualized
    - `tasks`: Array of all defined tasks
    - `videoRef`: Reference to the video element for synchronization

### Performance Considerations
- Video processing is computationally intensive - use requestAnimationFrame for UI updates
- Canvas drawing operations should be optimized to prevent frame drops
- Consider using web workers for heavy computational tasks

## Technical Implementation Details

### Bounding Box System
- **Creation & Interaction**: Canvas-based implementation in InteractiveOverlays.jsx
- **Persistence Strategy**: Keyframes with linear interpolation between marked frames
- **Performance Optimization**: Separate canvas layers for boxes vs landmarks

### Video Processing Pipeline
- **Frame Extraction**: Uses requestAnimationFrame for frame-by-frame processing
- **Landmark Detection**: Maps to bounding box coordinates using relative positioning
- **Task Analysis**: Processes frame sequences based on task start/end markers

### Waveform Visualization
- Implemented using customized WaveSurfer.js 
- Supports zoom controls through pixel-per-second ratio calculations
- Synchronizes with video playback via event listeners on timeupdate