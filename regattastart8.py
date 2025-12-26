#!/home/pi/yolov5_env/bin/python
import os
from common_module import (
    setup_camera,
    remove_picture_files,
    remove_video_files,
    restart_camera,
    start_video_recording,
    start_sequence,
    stop_video_recording,
    logger,
    text_rectangle,
    process_video,
    get_cpu_model,
    get_h264_writer,
)

from collections import deque
from datetime import datetime
import datetime as dt
import json
import numpy as np
import threading
import time
import cv2
import torch
import queue
import gc
import sys
import subprocess
import select

# --- YOLOv8 IMPORT ---
try:
    from ultralytics import YOLO
    logger.info("Ultralytics YOLOv8 library loaded")
except ImportError:
    logger.error("Ultralytics not found! Run: pip install ultralytics")

# Globala inställningar
fps = 15
crop_width, crop_height = 1440, 1080
video_path = '/var/www/html/images/'
photo_path = '/var/www/html/images/'
stop_event = threading.Event()
listen_thread = None
cpu_model = get_cpu_model()

pu_model = get_cpu_model()
logger.info("="*60)
logger.info(f"Starting new regattastart8.py session at {dt.datetime.now()}")
logger.info(f"Detected CPU model string: '{cpu_model}'")
logger.info("="*60)

# reset the contents of the status variable, used for flagging that
# video1-conversion is complete.
with open('/var/www/html/status.txt', 'w') as status_file:
    status_file.write("")


# --- MODELL-LADDNING (YOLOv8) ---
def load_yolov8_model(result_queue):
    try:
        start_time = time.time()
        # Sökväg till din tränade modell
        model_path = "/var/www/html/yolo8.pt"

        if not os.path.exists(model_path):
            logger.error(f"Model file not found at {model_path}")
            result_queue.put(None)
            return

        model = YOLO(model_path)

        # Optimera för CPU om möjligt
        if torch.__version__ >= "2.0":
            try:
                model.model = torch.compile(model.model)
                logger.info("Model compiled for CPU optimization")
            except:
                logger.info("Model compilation skipped")

        result_queue.put(model)
        logger.info(f"YOLOv8 model loaded in {time.time() - start_time:.2f}s")
    except Exception as e:
        logger.error(f"Error loading YOLOv8: {e}", exc_info=True)
        result_queue.put(None)


# --- INSPELNING OCH DETEKTERING ---
def finish_recording(camera, video_path, num_starts, video_end, start_time_dt, fps):
    # Konfiguration
    DETECTION_CONF_THRESHOLD = 0.5
    max_duration = (video_end + (num_starts-1)*5) * 60

    # Starta om kamera för Video 1
    camera = restart_camera(camera, resolution=(1920, 1080), fps=fps)

    # Ladda modellen via tråd
    res_q = queue.Queue()
    t = threading.Thread(target=load_yolov8_model, args=(res_q,))
    t.start()
    t.join(timeout=60)
    model = res_q.get_nowait()

    if model is None:
        logger.error("Could not proceed without YOLOv8 model")
        return

    # Beräkna crop och skalning
    frame = camera.capture_array()
    f_h, f_w = frame.shape[:2]
    shift_offset = 100
    x_start = max((f_w - crop_width) // 2 + shift_offset, 50)
    y_start = max((f_h - crop_height) // 2, 0)
    
    # YOLOv8 använder oftast 640x640 internt
    inf_w, inf_h = 640, 640
    scale_x = crop_width / inf_w
    scale_y = crop_height / inf_h

    # Video writer
    v1_h264 = os.path.join(video_path, "video1.h264")
    writer, _ = get_h264_writer(v1_h264, fps=fps, frame_size=(f_w, f_h), force_sw=True, logger=logger)

    # Logik-variabler
    pre_buffer = deque(maxlen=int(0.5 * fps))
    post_frames_left = 0
    last_detections = []
    in_seq = False
    origin = (40, int(f_h * 0.85))
    font = cv2.FONT_HERSHEY_DUPLEX
    frame_count = 0

    try:
        last_frame_ts = datetime.now()
        while not stop_event.is_set():
            if (datetime.now() - last_frame_ts).total_seconds() > 120: break

            frame = camera.capture_array()
            if frame is None: continue
            last_frame_ts = datetime.now()
            frame_count += 1
            ts = datetime.now()

            pre_buffer.append((frame_count, frame.copy(), ts))

            # Detektering varannan bild för att spara CPU
            if frame_count % 2 == 0:
                cropped = frame[y_start:y_start+crop_height, x_start:x_start+crop_width]
                resized = cv2.resize(cropped, (inf_w, inf_h))

                # Kör YOLOv8
                results = model.predict(resized, conf=DETECTION_CONF_THRESHOLD, verbose=False)[0]

                new_dets = []
                for box in results.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    # Skala om koordinater
                    nx1 = int(x1 * scale_x) + x_start
                    ny1 = int(y1 * scale_y) + y_start
                    nx2 = int(x2 * scale_x) + x_start
                    ny2 = int(y2 * scale_y) + y_start
                    new_dets.append((nx1, ny1, nx2, ny2, conf))
                last_detections = new_dets

            is_boat = len(last_detections) > 0

            if is_boat:
                post_frames_left = int(1.0 * fps)
                if not in_seq:
                    while pre_buffer:
                        _, b_f, b_ts = pre_buffer.popleft()
                        text_rectangle(b_f, f"{b_ts:%H:%M:%S} PRE", origin)
                        writer.write(b_f)
                    in_seq = True

                for (x1, y1, x2, y2, c) in last_detections:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, f"Sailboat {c:.2f}", (x1, y1-10), font, 0.7, (0, 255, 0), 2)

                text_rectangle(frame, ts.strftime("%H:%M:%S"), origin)
                writer.write(frame)

            elif post_frames_left > 0:
                text_rectangle(frame, f"{ts:%H:%M:%S} POST", origin)
                writer.write(frame)
                post_frames_left -= 1
            else:
                in_seq = False

            if (datetime.now() - start_time_dt).total_seconds() >= max_duration: break
            time.sleep(1/fps)

    finally:
        if writer: writer.release()
        process_video(video_path, "video1.h264", "video1.mp4", mode="remux")


# --- STANDARD FUNKTIONER FRÅN V9 ---
def listen_for_messages(stop_event):
    pipe_path = '/var/www/html/tmp/stop_recording_pipe'
    if os.path.exists(pipe_path): os.unlink(pipe_path)
    os.mkfifo(pipe_path)
    os.chmod(pipe_path, 0o666)

    while not stop_event.is_set():
        with open(pipe_path, 'r') as fifo:
            rlist, _, _ = select.select([fifo], [], [], 0.5)
            if rlist:
                if fifo.readline().strip() == 'stop_recording':
                    stop_event.set()
                    break
        time.sleep(0.1)


def main():
    camera = None
    global listen_thread
    try:
        camera = setup_camera()
        if camera is None: return 1

        if len(sys.argv) < 2: return 1
        form_data = json.loads(sys.argv[1])

        video_end = int(form_data["video_end"])
        num_starts = int(form_data["num_starts"])
        start_time_str = str(form_data["start_time"])
        dur_between_starts = int(form_data["dur_between_starts"])

        start_time_dt = dt.datetime.combine(dt.date.today(), dt.datetime.strptime(start_time_str, "%H:%M").time())
        if start_time_dt < dt.datetime.now(): start_time_dt += dt.timedelta(days=1)

        t5min = start_time_dt - dt.timedelta(minutes=5)
        while dt.datetime.now() < t5min: time.sleep(1)

        listen_thread = threading.Thread(target=listen_for_messages, args=(stop_event,), daemon=True)
        listen_thread.start()

        # Sekvens startar
        start_video_recording(camera, video_path, "video0.h264", resolution=(1640,1232), bitrate=4000000)
        start_sequence(camera, start_time_dt, num_starts, dur_between_starts, photo_path)

        last_start = start_time_dt + dt.timedelta(minutes=(num_starts - 1) * dur_between_starts)
        end_wait = last_start + dt.timedelta(minutes=2)
        while dt.datetime.now() < end_wait: time.sleep(1)

        stop_video_recording(camera)
        process_video(video_path, "video0.h264", "video0.mp4", mode="remux")

        # Starta YOLO-detektering (Video 1)
        finish_recording(camera, video_path, num_starts, video_end, start_time_dt, fps)

        with open('/var/www/html/status.txt', 'w') as f: f.write('complete')
        return 0

    except Exception as e:
        logger.error(f"Main error: {e}", exc_info=True)
        return 1
    finally:
        stop_event.set()
        if camera: camera.stop()

if __name__ == "__main__":
    sys.exit(main())
