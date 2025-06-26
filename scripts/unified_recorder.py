import sys
import pygame
import pygame.camera
import threading
import time
import numpy as np
import cv2
from queue import Queue
from PIL import ImageGrab, Image

class UnifiedRecorder:
    FPS = 4
    def __init__(self, platform_system=None, target_camera=None):
        # Determine platform inside constructor if not provided
        if platform_system is None:
            platform_system = sys.platform
            if platform_system.startswith('win'):
                platform_system = 'Windows'
            elif platform_system.startswith('linux'):
                platform_system = 'Linux'
            elif platform_system.startswith('darwin'):
                platform_system = 'Darwin'
        if platform_system == 'Windows':
            pygame.camera.init('_camera (MSMF)')
        else:
            pygame.camera.init()
        camlist = pygame.camera.list_cameras()
        img_size = (640, 360)
        self._camera = None
        if camlist:
            if target_camera and target_camera in camlist:
                self._camera = pygame.camera.Camera(target_camera, img_size)
            else:
                self._camera = pygame.camera.Camera(camlist[0], img_size)
        self.is_recording = False
        self.frame_queue = Queue()
        self.recording_thread = None
        self.recording_type = None
        self.fps = UnifiedRecorder.FPS
    def capture_screen_frames(self):
        while self.is_recording:
            frame = ImageGrab.grab()
            frame = np.array(frame)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            self.frame_queue.put(frame)
            time.sleep(1/self.fps)
    def capture_camera_frames(self):
        while self.is_recording:
            frame = self._camera.get_image()
            frame_buffer = pygame.surfarray.array3d(frame)
            frame_buffer = frame_buffer.transpose([1, 0, 2])
            frame_array = np.array(frame_buffer)
            frame_array = cv2.cvtColor(frame_array, cv2.COLOR_RGB2BGR)
            self.frame_queue.put(frame_array)
            time.sleep(1/self.fps)
    def start_recording(self, record_type='screen'):
        if self.is_recording:
            print("Recording is already in progress")
            return False
        if record_type not in ['screen', 'camera']:
            print("Invalid record type. Use 'screen' or 'camera'")
            return False
        if record_type == 'camera' and self._camera is None:
            print("Camera is not available")
            return False
        self.is_recording = True
        self.recording_type = record_type
        if record_type == 'screen':
            self.recording_thread = threading.Thread(target=self.capture_screen_frames)
        else:
            self.recording_thread = threading.Thread(target=self.capture_camera_frames)
        self.recording_thread.start()
        print(f"Started {record_type} recording...")
        return True
    def stop_recording(self, output_filename, resize_width=640):
        if not self.is_recording:
            print("No recording in progress")
            return None
        self.is_recording = False
        self.recording_thread.join()
        if self.frame_queue.empty():
            print("No frames captured")
            return None
        if(output_filename):
            first_frame = self.frame_queue.queue[0]
            height, width = first_frame.shape[:2]
            new_width = int(resize_width)
            new_height = int(resize_width / width * height)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(
                output_filename,
                fourcc,
                1,
                (new_width, new_height),
                True
            )
            print("Processing and saving video...")
            frame_count = 0
            while not self.frame_queue.empty():
                frame = self.frame_queue.get()
                frame = cv2.GaussianBlur(frame, (3, 3), 0)
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
                frame = np.uint8(frame)
                out.write(frame)
                frame_count += 1
            out.release()
            print(f"Video saved to: {output_filename} ({frame_count} frames)")
        self.frame_queue.queue.clear()
        return output_filename

    def grab_screen(self, resize_factor=0.5):
        """
        Capture the screen and return a PIL Image object. Optionally resize by a factor (e.g., 0.5 for half size).
        Returns None on failure.
        """
        try:
            screenshot = ImageGrab.grab()
            if resize_factor and resize_factor != 1.0:
                width, height = screenshot.size
                new_width = int(width * resize_factor)
                new_height = int(height * resize_factor)
                screenshot = screenshot.resize((new_width, new_height), Image.LANCZOS)
            return screenshot
        except Exception as e:
            print(f"grab_screen error: {e}")
            return None
