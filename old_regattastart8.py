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
import threading
import time
import cv2
import torch
import queue
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
ENABLE_PRE_POST_FRAMES = False  # Set to True to re-enable pre/post buffering

logger.info("="*60)
logger.info(f"Starting new regattastart8.py session at {dt.datetime.now()}")
logger.info(f"Detected CPU model string: '{cpu_model}'")
logger.info("="*60)


def _iou(box_a, box_b):
    """Beräknar Intersection-over-Union mellan två (x1, y1, x2, y2) boxar."""
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    return inter / float(area_a + area_b - inter)


def save_uncertain_image(frame, detections, current_count, max_images=300,
                          folder='/var/www/html/images/training_data/',
                          last_save_time=0.0, min_interval_seconds=30.0,
                          last_save_bbox=None, iou_dedup_threshold=0.5):
    """Sparar bilden vid osäkerhet, upp till max_images stycken.

    En cooldown förhindrar spam, men om en osäker detektion dyker upp på en
    tydligt ANNAN plats i bilden (låg IoU mot senast sparade box) sparas den
    ändå direkt - annars skulle t.ex. en båt som långsamt tar ner seglen vid
    mållinjen kunna generera dussintals nästan identiska bilder av samma
    händelse, istället för ett varierat urval av olika osäkra fall.
    """
    if current_count >= max_images:
        return False, last_save_time, last_save_bbox  # Gränsen nådd

    now = time.time()

    for (x1, y1, x2, y2, conf) in detections:
        # Om vi hittar en båt med konfidens mellan 20% och 45%
        if 0.20 <= conf <= 0.45:
            box = (x1, y1, x2, y2)
            same_spot = (
                last_save_bbox is not None
                and _iou(box, last_save_bbox) >= iou_dedup_threshold
            )
            if same_spot and (now - last_save_time) < min_interval_seconds:
                continue  # Samma objekt/plats som senast - hoppa över, testa nästa detektion

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{folder}uncertain_{timestamp}.jpg"

            # Spara en ren bild utan boxar för träning
            cv2.imwrite(filename, frame)
            logger.info(f"Saved uncertain detection #{current_count+1} (conf: {conf:.2f})")
            return True, now, box  # Bild sparad, uppdatera tidsstämpel och senaste position

    return False, last_save_time, last_save_bbox


# --- MODELL-LADDNING (YOLOv8) ---
def load_yolov8_model(result_queue):
    try:
        start_time = time.time()
        # Sökväg till din tränade modell
        model_path = "/opt/regattastart/models/yolov8.pt"

        if not os.path.exists(model_path):
            logger.error(f"Model file not found at {model_path}")
            result_queue.put(None)
            return

        model = YOLO(model_path)

        # Optimera för CPU om möjligt
        if torch.__version__ >= "2.0":
            model.model = torch.compile(model.model)
            logger.info("Model compiled for CPU optimization")

        result_queue.put(model)
        logger.info(f"YOLOv8 model loaded in {time.time() - start_time:.2f}s")
    except Exception as e:
        logger.error(f"Error loading YOLOv8: {e}", exc_info=True)
        result_queue.put(None)


# --- INSPELNING OCH DETEKTERING ---
def finish_recording(camera, video_path, num_starts, video_end, start_time_dt, fps):
    # Konfiguration
    DETECTION_CONF_THRESHOLD = 0.5
    UNCERTAIN_CONF_FLOOR = 0.20  # Lägre golv så YOLO även returnerar osäkra boxar
    last_adjustment = time.time()
    max_duration = (video_end + (num_starts-1)*5) * 60

    # Säkerställ att mappen för träningsdata finns, annars misslyckas cv2.imwrite tyst
    os.makedirs('/var/www/html/images/training_data/', exist_ok=True)

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
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
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

    # Annotation inställningar (Banner-position)
    origin = (40, int(f_h * 0.85))
    font = cv2.FONT_HERSHEY_DUPLEX
    frame_count = 0

    # --- Initiera utanför loopen ---
    uncertain_saved_total = 0 # Räknare för denna session
    last_uncertain_save_time = 0.0 # Cooldown-tidsstämpel mellan sparade osäkra bilder
    last_uncertain_save_bbox = None # Position för senast sparad osäker bild (för spatial dedup)
    last_adjustment = time.time()
    skip_factor = 2

    try:
        last_frame_ts = datetime.now()
        while not stop_event.is_set():
            if (datetime.now() - last_frame_ts).total_seconds() > 120: 
                logger.error("Watchdog: Camera frozen")
                break

            frame = camera.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            if frame is None: continue
            last_frame_ts = datetime.now()
            frame_count += 1
            ts = datetime.now()

            pre_buffer.append((frame_count, frame.copy(), ts))

            if time.time() - last_adjustment > 30:
                temp = get_cpu_temp()
                throttle = get_throttle_status()

                if temp is not None:
                    # Logik för AI-belastning (Skip Factor)
                    if temp > 80:
                        skip_factor = 5  # Kör AI mer sällan vid hetta
                        logger.warning(f"High temp ({temp:.1f}C) -> Increasing skip_factor to {skip_factor}")
                    elif temp < 72:
                        skip_factor = 2  # Gå tillbaka till standard när det svalnat
                        logger.debug(f"Cooler temp ({temp:.1f}C) -> Resetting skip_factor to {skip_factor}")

                    # Logik för Bildhastighet (FPS)
                    if temp > 84: # Lite högre tröskel för att sänka FPS
                        fps = max(5, fps - 2)
                        logger.warning(f"Critical temp ({temp:.1f}C) -> Reducing FPS to {fps}")
                    elif temp < 70 and fps < 15:
                        fps = min(15, fps + 1)
                        logger.info(f"Safe temp ({temp:.1f}C) -> Increasing FPS to {fps}")

                logger.info(f"System Check: Temp={temp:.1f}C, Skip={skip_factor}, FPS={fps}, Throttle=0x{throttle:x}")
                last_adjustment = time.time()

            # --- INFERENCE (Varannan frame för att spara CPU) ---
            if frame_count % skip_factor == 0:
                cropped = frame[y_start:y_start+crop_height, x_start:x_start+crop_width]
                resized = cv2.resize(cropped, (inf_w, inf_h))

                # Kör YOLOv8 med lågt golv så osäkra detektioner också returneras
                results = model.predict(resized, conf=UNCERTAIN_CONF_FLOOR, verbose=False)[0]

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

                # Endast säkra detektioner styr inspelning/ritning av boxar
                last_detections = [d for d in new_dets if d[4] >= DETECTION_CONF_THRESHOLD]

                # Spara osäkra bilder för framtida annotering (från ALLA detektioner, inkl. lågkonfidens)
                # NYTT: Kolla om vi ska spara träningsdata
                if new_dets:
                    was_saved, last_uncertain_save_time, last_uncertain_save_bbox = save_uncertain_image(
                        frame, new_dets, uncertain_saved_total,
                        max_images=300, last_save_time=last_uncertain_save_time,
                        min_interval_seconds=30.0, last_save_bbox=last_uncertain_save_bbox
                    )
                    if was_saved:
                        uncertain_saved_total += 1

            is_boat = len(last_detections) > 0

            if is_boat:
                post_frames_left = int(1.0 * fps)
                if not in_seq:
                    if ENABLE_PRE_POST_FRAMES:
                        while pre_buffer:
                            _, b_f, b_ts = pre_buffer.popleft()
                            label_pre = f"{b_ts:%Y-%m-%d %H:%M:%S} PRE"
                            text_rectangle(b_f, label_pre, origin)
                            writer.write(b_f)
                    else:
                        pre_buffer.clear()  # töm bufferten även när vi inte skriver den, annars växer den i minnet
                    in_seq = True

                for (x1, y1, x2, y2, c) in last_detections:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                    cv2.putText(frame, f"{c:.2f} {ts:%H:%M:%S}", (x1, y1-15), font, 0.8, (0, 255, 0), 2)

                text_rectangle(frame, f"{ts:%Y-%m-%d %H:%M:%S}", origin)
                # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                writer.write(frame)

            elif ENABLE_PRE_POST_FRAMES and post_frames_left > 0:
                # Ingen båt i just denna bild, men vi filmar vidare (POST-fas)
                label_post = f"{ts:%Y-%m-%d %H:%M:%S} POST"
                text_rectangle(frame, label_post, origin)
                # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                writer.write(frame)
                post_frames_left -= 1
            else:
                in_seq = False

            if (datetime.now() - start_time_dt).total_seconds() >= max_duration: 
                logger.info("Max duration reached for Video 1")
                break

            time.sleep(1/fps)
    except Exception as e:
        logger.error(f"Error in finish_recording loop: {e}", exc_info=True)
    finally:
        if writer:
            writer.release()
            logger.info(f"Video writer released: {v1_h264}")
        # Konvertera till MP4
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


def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return int(f.read()) / 1000.0  # °C
    except FileNotFoundError:
        return None


def get_throttle_status():
    try:
        output = subprocess.check_output(["vcgencmd", "get_throttled"]).decode().strip()
        return int(output.split('=')[1], 16)
    except Exception:
        return 0


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

        # Rensa gamla bilder (jpg)
        remove_picture_files(photo_path, ".jpg")  # clean up
        # Rensa gamla videofiler (både råa .h264 och färdiga .mp4)
        remove_video_files(photo_path, "video")  # clean up
        # Rensa status-filen så att webbsidan nollställs
        if os.path.exists('/var/www/html/status.txt'):
            with open('/var/www/html/status.txt', 'w') as f:
                f.write('recording')

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
