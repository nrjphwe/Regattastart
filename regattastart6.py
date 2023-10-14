import os
import sys
import cgitb
cgitb.enable(display=0, logdir="/var/www/html/")
import time
from datetime import datetime
import datetime as dt
import logging
import logging.config
import subprocess
import RPi.GPIO as GPIO
from picamera import PiCamera, Color
signal_dur = 1 # 1 sec
mp4_path = '/var/www/html/images/'

def setup_logging():
    logging.config.fileConfig('logging.conf')
    logger = logging.getLogger('Start')
    logger.info(" Start logging")
    return logger

def setup_camera():
    camera = PiCamera()
    camera.resolution = (1296, 730)
    camera.framerate = 5
    camera.annotate_background = Color('black')
    camera.annotate_foreground = Color('white')
    # camera.rotation = (180) # Depends on how camera is mounted
    return camera

ON = GPIO.HIGH
OFF = GPIO.LOW

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(True)
    signal = 26
    lamp1 = 20
    lamp2 = 21
    GPIO.setup(signal, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(lamp1, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(lamp2, GPIO.OUT, initial=GPIO.HIGH)
    return signal, lamp1, lamp2

def remove_files(directory, pattern):
    files = os.listdir(directory)
    for file in files:
        if file.startswith(pattern):
            file_path = os.path.join(directory, file)
            os.remove(file_path)

def trigger_warning_signal(signal):
    GPIO.output(signal, ON)
    logger.info (" Signal set for %s sec", signal_dur)
    time.sleep(signal_dur)
    GPIO.output(signal, OFF)

def capture_picture(camera, photo_path, file_name):
    camera.capture(os.path.join(photo_path, file_name), use_video_port=True)
    logger.info (" capture picture %s ", file_name)
    
def start_video_recording(camera, mp4_path, file_name):
    if camera.recording:
        camera.stop_recording()
    camera.start_recording(os.path.join(mp4_path, file_name))
    logger.info (" Recording of %s started", file_name)

def stop_video_recording(camera):
    camera.stop_recording()
    logger.info (" video recording stopped")

def convert_video_to_mp4(mp4_path, source_file, destination_file):
    convert_video_str = "MP4Box -add {} -new {}".format(os.path.join(mp4_path,source_file), os.path.join(mp4_path,destination_file))
    subprocess.run(convert_video_str, shell=True)
    logger.info (" Video recording %s converted ", destination_file)

def main():
    camera = None # Initialize the camera variable
    signal = None # Initialize the signal relay/variable
    try:
        start_time = str(sys.argv[1])
        week_day = str(sys.argv[2])
        video_delay = int(sys.argv[3])
        num_videos = int(sys.argv[4])
        video_dur = int(sys.argv[5])
        # Set up initial data
        photo_path = '/var/www/html/images/'
        
        global logger  # Make logger variable global
        logger = setup_logging()
        logger.info (" Start_time = %s", start_time)
        start_hour, start_minute = start_time.split(':')
        start_time_sec = 60 * (int(start_minute) + 60 * int(start_hour)) # 6660
        logger.info (' Weekday = %s', week_day)
        signal, lamp1, lamp2 = setup_gpio()
        camera = setup_camera()
        remove_files(photo_path, "video")
        remove_files(photo_path, "pict")
        while ( True ):
            try:
                now = dt.datetime.now()
                wd = dt.datetime.today().strftime("%A")
                if wd == week_day :            # example Wednesday = 3
                    t = dt.datetime.now() # ex: 2015-01-04 18:48:33.255145
                    time_now = t.strftime('%H:%M:%S')   # 18:48:33
                    nh, nm, ns = time_now.split(':')
                    seconds_now =  60 * (int(nm) + 60 * int(nh)) + int(ns)
                    camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    #-------------------------------------------------------------#
                    #    Varningssignal === 5 minute signal before start
                    #-------------------------------------------------------------#
                    if seconds_now == (start_time_sec - 5*60) :
                        start_video_recording(camera, photo_path, "video0.h264")
                        trigger_warning_signal(signal)
                        capture_picture(camera, photo_path, "1st-5min_pict.jpg")
                        GPIO.output(lamp1, ON)    # Lamp1 On (Flag O)
                        logger.info (" 5 min Lamp-1 On -- Up with Flag O")
                    #-------------------------------------------------------------#
                    # $$$$  Forberedelsesignal 4 minutes
                    #-------------------------------------------------------------#
                    if seconds_now == (start_time_sec - 4*60):
                        trigger_warning_signal(signal)
                        logger.info (" Prep-signal 4 min before start, for 1 sec")
                        capture_picture(camera, photo_path, "1st-4min_pict.jpg")
                        GPIO.output(lamp2, ON)    # Lamp 2 On (Flag P)
                        logger.info (" 4 min Lamp-2 On  --- Up with Flag P ")
                    #------------------------------------------------------------#
                    # $$$$ One-Minute-to-start signal
                    #------------------------------------------------------------#
                    if seconds_now == (start_time_sec - 1*60):
                        trigger_warning_signal(signal)
                        logger.info (" 1 minute before start, signal on for 1 sec")
                        capture_picture(camera, photo_path, "1st-1min_pict.jpg")
                        logger.info (" 1 min  Lamp-2 Off -- Flag P down")
                        GPIO.output(lamp2, OFF)    # Lamp 2 Off (Flag P)
                    #-------------------------------------------------------------#
                    #$$$$ Start signal
                    #-------------------------------------------------------------#
                    if seconds_now == start_time_sec:
                        s_start = time.time()  # will be used for annotations of seconds
                        print ("  ===       ==========             =               =======        ==========")
                        print (" =    =         =                 =  =             =       =           =")
                        print ("=               =                =    =            =        =          =")
                        print (" =              =               =      =           =       =           =")
                        print ("  = =           =              =========           =======             = ")
                        print ("      =         =             =          =         =    =              =")
                        print ("       =        =            =            =        =     =             =")
                        print (" =    =         =           =              =       =      =            =")
                        print ("  ===           =          =                =      =       =           =")
                        print (" ")
                        GPIO.output(lamp1, OFF)    # Lamp 1 Off (Flag O)
                        trigger_warning_signal(signal)
                        capture_picture(camera, photo_path, "1st-start_pict.jpg")
                        logger.info (" Wait 2 minutes after start, then stop video recording")
                        camera.wait_recording(118)
                        stop_video_recording(camera)
                        logger.info (" video 0 recording stopped")
                        convert_video_to_mp4(mp4_path, "video0.h264", "video0.mp4")
                        logger.info (" video 0 converted to mp4 format")
                        #----------------------------------------------------------#
                        # Wait for delay/finish, when next video1 will start, video_delay
                        #----------------------------------------------------------#
                        t = dt.datetime.now()
                        logger.info (" Time now: %s", t.strftime('%H:%M:%S'))
                        sum = video_delay - 2  # Delay in minutes
                        while sum > 0:
                            sum = sum - 1
                            time.sleep(60)
                            logger.info (' sum: %s', sum)
                        #----------------------------------------------------------#
                        # end while loop, delay from 2 minutes after start to video1
                        #----------------------------------------------------------#
                        # Result video, duration at "video_dur"
                        #----------------------------------------------------------#
                        logger.info (" num_videos = %s",num_videos)
                        logger.info (' video duration = %s', video_dur)
                        stop = num_videos+1
                        for i in range(1, stop):
                            start_video_recording(camera, photo_path, "video" + str(i) + ".h264")
                            logger.info (' Started recording of video%s', i)
                            logger.info (' i = %s', i)
                            #------------------------------------------------------#
                            t = dt.datetime.now()
                            logger.info (" Time now: %s", t.strftime('%H:%M:%S'))
                            #------------------------------------------------------#
                            # video running, duration at "video_dur"
                            #------------------------------------------------------#
                            while (dt.datetime.now() - t).seconds < (60 * video_dur):
                                camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "  " + str(int((time.time()-s_start)))
                                camera.wait_recording(0.5)
                            stop_video_recording(camera)
                            logger.info (" video%s recording stopped", i)
                            logger.info (" Time now: %s", t.strftime('%H:%M:%S'))
                            logger.info (" convert video %s to mp4 format", i)
                            convert_video_to_mp4(mp4_path, "video" + str(i) + ".h264",  "video" + str(i) + ".mp4")
                            logger.info (' converted h264 video to mp4 of video%s', i)
                        logger.info (" This was the last video =====")
            except Exception as e:
                logger.exception("Exception in inner loop: %s", str(e))
            finally:
                if camera is not None:
                    camera.close()  # Release the camera resources
                    logger.info (" camera.close  =======")
                if signal is not None:
                    GPIO.output(signal, OFF)  # Turn off the signal output
                    GPIO.cleanup()
        except OSError as err:
            logger.warning ("OS error: {0}".format(err))
        #except Exception as e:
        #    logger.exception("Fatal error in main loop: %s", str(e)) 
if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)  # Set log level to WARNING
    main()
