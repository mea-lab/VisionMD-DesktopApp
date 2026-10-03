import cv2
import numpy as np
from tqdm import tqdm


def video_reader(filename: str, batch_size: int = 8, width: int | None = None):
    """
    Read a video file and yield frames in batches.

    Frames are decoded with OpenCV in bounded batches. This also optionally
    downsamples the video when compute is limited.

    Args:
        filename: (str) The path to the video file.
        batch_size: (int) The number of frames to yield at once.
        width: (int | None) The width to downsample to. If None, the original width is used.

    Returns:
        A generator that yields batches
    """

    cap = cv2.VideoCapture(filename)

    frames = []
    while True:

        ret, frame = cap.read()

        if ret is False:

            if len(frames) > 0:
                frames = np.array(frames)
                yield frames

            cap.release()
            return

        else:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            if width is not None:
                # downsample to keep the aspect ratio and output the specified width
                scale = width / frame.shape[1]
                height = int(frame.shape[0] * scale)
                frame = cv2.resize(frame, (width, height))

            frames.append(frame)

            if len(frames) >= batch_size:
                frames = np.array(frames)
                yield frames

                frames = []
