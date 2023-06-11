import os
import sys
import time
import logging
import subprocess
from datetime import datetime
import RPi.GPIO as GPIO
from picamera import PiCamera, Color

def setup_logging():
    logging.config.fileConfig('logging.conf')
    logger = logging.getLogger('Start')
    logger.info("Start logging")
    return logger

def setup_camera():
    camera = PiCamera()
    camera.resolution = (1296, 730)
    camera.framerate = 5
    camera.annotate_background = Color('black')
    camera.annotate_foreground = Color('white')
    # camera.rotation = (180) # Depends on how camera is mounted
    return camera

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

# Function to trigger the warning signal
def trigger_warning_signal():
    GPIO.output(signal, ON)
    time.sleep(signal_dur)
    GPIO.output(signal, OFF)

# Function to capture a picture with overlay
def capture_picture(camera, file_name, text):
    camera.annotate_text = text
    camera.capture(file_name, use_video_port=True)

# Function to start video recording
def start_video_recording(camera, file_name):
    camera.start_recording(file_name)

# Function to stop video recording
def stop_video_recording(camera):
    camera.stop_recording()

# Function to convert the video format from h264 to mp4
def convert_video_to_mp4(source_file, destination_file):
    convert_video_str = "MP4Box -add {} -new {}".format(source_file, destination_file)
    subprocess.run(convert_video_str, shell=True)
   
# Main function
def main():
    
    start_time = str(sys.argv[1])
    week_day = str(sys.argv[2])
    video_delay = int(sys.argv[3])
    num_videos = int(sys.argv[4])
    video_dur = int(sys.argv[5])
    
    # Set up initial data  
    photo_path = '/var/www/html/images/'
    mp4_path = '/var/www/html/images/'
    photo_name = 'latest.jpg'
    signal_dur = 0.3 # 0.3 sec
  
    logger.info (" Start_time = %s", start_time)
    start_hour, start_minute = start_time.split(':')
    start_time_sec = 60 * (int(start_minute) + 60 * int(start_hour)) # 6660
    logger.info (' Weekday = %s', week_day)
    
    remove_files(photo_path, "video")
    remove_files(photo_path, "pict")    
    #-----------------------------------------------------------------#
    while ( True ):
        try:      
            now = dt.datetime.now()
            wd = dt.datetime.today().strftime("%A")
            if wd == week_day :            # example Wednesday = 3
                t = dt.datetime.now() # ex: 2015-01-04 18:48:33.255145
                time_now = t.strftime('%H:%M:%S')   # 18:48:33
                nh, nm, ns = time_now.split(':')
                seconds_now =  60 * (int(nm) + 60 * int(nh)) + int(ns) 
                start_video_recording(camera, photo_path, video0.h264) 
                camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                #-------------------------------------------------------------#
                #    Varningssignal === 5 minute signal before start
                #-------------------------------------------------------------#
                if seconds_now == (start_time_sec - 5*60) :
                    trigger_warning_signal()
                    capture_picture(camera, photo_path, "1st-5min_pict.jpg")
                    GPIO.output(lamp1, ON)    # Lamp1 On (Flag O)
                    logger.info (" 5 min Lamp-1 On -- Up with Flag O")
                #-------------------------------------------------------------#
                # $$$$  Forberedelsesignal 4 minutes
                #-------------------------------------------------------------#
                if seconds_now == (start_time_sec - 4*60):
                    trigger_warning_signal()
                    logger.info (" Prep-signal 4 min before start, for 1 sec")
                    capture_picture(camera, photo_path, "1st-4min_pict.jpg")
                    GPIO.output(lamp2, ON)    # Lamp 2 On (Flag P)
                    logger.info (" 4 min Lamp-2 On  --- Up with Flag P ")
                #------------------------------------------------------------#
                # $$$$ One-Minute-to-start signal
                #------------------------------------------------------------#
                if seconds_now == (start_time_sec - 1*60):
                    trigger_warning_signal()
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
                    trigger_warning_signal()
                    capture_picture(camera, photo_path, "1st-start_pict.jpg")
                    logger.info (" Wait 2 minutes then stop video recording")
                    while (dt.datetime.now() - t).seconds < 118:
                        camera.wait_recording(1)
                    stop_recording(camera)
                    logger.info (" video 0 recording stopped")
                    #-------------------------------------------------------#
                    # convert video0 format from h264 to mp4
                    #-------------------------------------------------------#
                    convert_video(video0.h264, video0.mp4)
                    logger.info (" video 0 converted to mp4 format")
                    #----------------------------------------------------------#
                    # Wait for finish, when next video1 will start, video_delay
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
                        start_video_recording(camera, photo_path, "video0"+str(i) + ".h264") 
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
                        stop_recording(camera)
                        logger.info (" This was the last video =====")
                        for i in range(1, stop):
                            logger.info ('i = %s', i)
                            t = dt.datetime.now()
                            logger.info (" Time now: %s", t.strftime('%H:%M:%S'))
                            logger.info (" convert video %s to mp4 format", i)
                            convert_video ("video" + str(i) + ".h264",  "video" + str(i) + ".mp4 ")
            logger.info ("========    Finished   =======")
            logger.info ("==============================")
            break
        except KeyboardInterrupt:
                logger.info ("======= Stopped by Ctrl-C =====")
                break
        except IOError as e:
            logger.warning ("I/O error({0}): {1}".format(e.errno, e.strerror))
        except ValueError:
            logger.warning ("Could not convert data to an integer.")
        #except Exception as e:
        #    logging.warning ("Unexpected exception! %s",e)
        except Exception:
            logger.info("Fatal error in main loop", exc_info=True)
            #logger.exception("Fatal error in main loop")
        except OSError as err:
            logger.warning ("OS error: {0}".format(err))
    GPIO.cleanup()
