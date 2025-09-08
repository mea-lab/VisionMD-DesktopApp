# VideoPlayer Component Documentation

## Overview

The `VideoPlayer` directory contains the core components responsible for video playback, visualization, and interactive manipulations within the VideoAnalysisToolFrontend. This system provides frame-accurate playback, overlay capabilities for bounding boxes and landmarks, and interactive elements for task selection and analysis.

## Directory Structure

```
VideoPlayer/
├── VideoPlayer.jsx      # Main container component
├── VideoControls.jsx    # Playback control interface
├── VideoDrawer.jsx      # Canvas-based overlay rendering
└── InteractiveOverlays.jsx # SVG-based interactive elements
```

## Component Details

### VideoPlayer.jsx

The main container that coordinates all video playback and visualization features.

**Key Responsibilities:**
- Video source management and playback
- Zoom and pan functionality
- Container for overlays and interactive elements
- Frame counting and navigation
- Synchronization between video time and UI

**Notable Implementation Details:**
- Uses `requestAnimationFrame` for frame-accurate updates
- Manages dynamic zoom with transform-origin preservation
- Coordinates multiple canvas/SVG layers for different visualizations
- Handles pointer events for interactive pan/zoom

### VideoControls.jsx

Provides the UI controls for video playback and navigation.

**Key Responsibilities:**
- Play/pause functionality
- Frame-by-frame navigation
- Keyboard shortcut handling

**Technical Details:**
- Implements keyboard shortcuts (arrow keys, space bar)
- Provides frame-level precision navigation
- Implements error checking for video loading state

### VideoDrawer.jsx

Handles canvas-based rendering of overlays on the video.

**Key Responsibilities:**
- Drawing bounding boxes for subject tracking
- Rendering landmark data for selected tasks
- Synchronizing with the video playback

**Implementation Details:**
- Uses `requestVideoFrameCallback` for frame-synchronized rendering
- Implements separate rendering paths for different screen contexts
- Optimized redraw strategy to prevent unnecessary rendering

### InteractiveOverlays.jsx

Provides SVG-based interactive elements for manipulating tasks and bounding boxes.

**Key Responsibilities:**
- Interactive resize handles for task boxes
- Draggable task regions
- Visual indicators for subject tracking
- Task selection visualization

**Technical Details:**
- Implements custom resize handles with `ResizeHandles` component
- SVG-based interaction for precise coordinate mapping
- Coordinate transformation for correct pointer events
- Event handling for drag and resize operations

## State Management

The VideoPlayer components interact with several key state objects:

1. **Video State**
    - `videoRef` - Direct reference to the HTML video element
    - `videoURL` - Source URL for the video
    - `fps` - Frames per second for accurate timing calculations

2. **Visual Overlays**
    - `boundingBoxes` - Array of frame-indexed bounding box data
    - `taskBoxes` - Task regions with coordinates and timing data
    - `landMarks` - Point data for visualization on specific frames

3. **Interaction State**
    - `zoomLevel` - Current zoom magnification
    - `panOffset` - X/Y offset for pan position
    - `currentFrame` - Current frame number

## Key Technical Implementation Features

### Coordinate Systems

The components handle multiple coordinate systems:
- **Video coordinates**: Native dimensions of the video
- **Canvas/SVG coordinates**: Scaled with zoom and pan transformations
- **Client coordinates**: Browser viewport positioning

### Performance Optimization

- Separate canvas and SVG layers to optimize rendering paths
- Frame-based callbacks for synchronization with video playback
- Selective redrawing based on frame changes

### Interactive Element Handling

- Custom pointer event handling for drag and resize operations
- SVG point transformation for accurate coordinate mapping
- Resize constraints to maintain minimum dimensions

## Development Guidelines

### Adding New Overlay Types

1. Add the data structure to the appropriate state object
2. Implement drawing logic in `VideoDrawer.jsx`
3. Add interactive controls in `InteractiveOverlays.jsx` if needed

### Performance Considerations

- Prefer canvas-based rendering for high-frequency updates (landmarks, tracking)
- Use SVG for interactive elements that require precise hit detection
- Consider debouncing frame updates for heavy operations

### Video Frame Access

- Use `requestVideoFrameCallback` for frame-accurate operations
- Calculate frame numbers via: `Math.round(timestamp * fps)`
- Ensure operations are synchronized with the video's natural frame rate