#!/usr/bin/python3 -u
import os
import sys
import time
import subprocess
from picamera import PiCamera, Color
import RPi.GPIO as GPIO

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
    # camera.brightness = 70
    # camera.hflip = True
    # camera.vflip = True
    # camera.rotation = (180) # Depends on how camera is mounted
    # ribbon down 0, ribbon up 180
    return camera

def remove_files(directory, pattern):
    files = os.listdir(directory)
    for file in files:
        if file.startswith(pattern):
            file_path = os.path.join(directory, file)
            os.remove(file_path)
    
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

def capture_picture(camera, photo_path, filename):
    camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    camera.capture(photo_path + filename, use_video_port=True)

def start_recording(camera, path, filename):
    camera.start_recording(os.path.join(path, filename))

def stop_recording(camera):
    camera.stop_recording()

def convert_video(input_file, output_file):
    convert_video_str = f"MP4Box -add {input_file} -new {output_file}"
    subprocess.run(convert_video_str, shell=True)

# Function to trigger the warning signal
def trigger_warning_signal():
    GPIO.output(signal, ON)
    time.sleep(signal_dur)
    GPIO.output(signal, OFF)
   
# Main function
def main():   
    start_time = str(sys.argv[1])
    week_day = str(sys.argv[2])
    video_delay = int(sys.argv[3])
    num_videos = int(sys.argv[4])
    video_dur = int(sys.argv[5])
    
    signal_dur = 0.3 # 0.3 sec
    
    logger = setup_logging()
    camera = setup_camera()
    signal, lamp1, lamp2 = setup_gpio()

    photo_path = '/var/www/html/images/'
    mp4_path = '/var/www/html/images/'

    remove_files(photo_path, "video")
    remove_files(photo_path, "pict")
    
    start_hour, start_minute = start_time.split(':')
    start_time_sec = 60 * (int(start_minute) + 60 * int(start_hour))
    logger.info(' Weekday = %s', week_day)
    
    #-----------------------------------------------------------------#
    while ( True ):
        now = dt.datetime.now()
        wd = dt.datetime.today().strftime("%A")
        if wd == week_day :            # example Wednesday = 3
            t = dt.datetime.now() # ex: 2015-01-04 18:48:33.255145
            time_now = t.strftime('%H:%M:%S')   # 18:48:33
            nh, nm, ns = time_now.split(':')
            seconds_now =  60 * (int(nm) + 60 * int(nh)) + int(ns)
            camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            #-------------------------------------------------------------#
            #
            #    Varningssignal === 5 minute signal before start
            #
            #-------------------------------------------------------------#
            if seconds_now == (start_time_sec - 5*60) :
                trigger_warning_signal()
                capture_picture(camera, photo_path + "1st-5min_pict.jpg", "5 min " + dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                GPIO.output(lamp1, ON)    # Lamp1 On (Flag O)
                logger.info (" 5 min Lamp-1 On -- Up with Flag O")
            #-------------------------------------------------------------#
            # $$$$  Forberedelsesignal 4 minutes
            #-------------------------------------------------------------#
            if seconds_now == (start_time_sec - 4*60):
                trigger_warning_signal()
                capture_picture(camera, photo_path + "1st-4min_pict.jpg", "4 min " + dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                logger.info (" Prep-signal 4 min before start, for 1 sec")
                GPIO.output(lamp2, ON)    # Lamp 2 On (Flag P)
                logger.info (" 4 min Lamp-2 On  --- Up with Flag P ")
            #------------------------------------------------------------#
            # $$$$ One-Minute-to-start signal
            #------------------------------------------------------------#
            if seconds_now == (start_time_sec - 1*60):
                trigger_warning_signal()
                capture_picture(camera, photo_path + "1st-1min_pict.jpg", "1 min " + dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                logger.info (" 1 minute before start, signal on for 1 sec")
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
                capture_picture(camera, photo_path + "1st-start_pict.jpg", "start " + dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                logger.info (" Wait 2 minutes then stop video recording")
                while (dt.datetime.now() - t).seconds < 118:
                    camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    camera.wait_recording(1)
                #-------------------------------------------------------#
                # stop video0 recording
                #-------------------------------------------------------#
                camera.stop_recording()
                logger.info (" video 0 recording stopped")

                #-------------------------------------------------------#
                # convert video0 format from h264 to mp4
                #-------------------------------------------------------#
                from subprocess import CalledProcessError
                convert_video_str = "MP4Box" + " -add " + photo_path + "video0.h264 " + "-new " + mp4_path + "video0.mp4 "
                convert_video = convert_video_str.encode(encoding='utf8')
                logger.info (" convert_video: {convert_video}")
                #---------------------------------------------------------------------------------------#
                # https://stackoverflow.com/questions/45040261/python-3-auto-conversion-from-h264-to-mp4
                #---------------------------------------------------------------------------------------#
                logger.info (" >>>>>> try convert video 0 to mp4 format")
                try:
                    output = subprocess.run(convert_video, shell=True)
                except:
                    logger.info (" failure to output to mp4")
                else:
                    logger.info (" video 0 converted to mp4 format")
                finally:
                    subprocess.run(convert_video, shell=True)
                    logger.info (" video 0 converted again to mp4 format")
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
                    camera.start_recording(photo_path + "video" + str(i) + ".h264")
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
                    #------------------------------------------------------#
                    #  stop video recording
                    #------------------------------------------------------#
                    camera.stop_recording()
                    #------------------------------------------------------#
                    t = dt.datetime.now()
                    logger.info (" Time now: %s", t.strftime('%H:%M:%S'))
                    #------------------------------------------------------#
                    logger.info ('stopped recording video%s', i)
                logger.info ("==============================")
                logger.info (" This was the last video =====")
                logger.info ("==============================")
                for i in range(1, stop):
                    logger.info ('i = %s', i)
                    t = dt.datetime.now()
                    logger.info (" Time now: %s", t.strftime('%H:%M:%S'))
                    # Camera running convert previous made video #
                    logger.info (" convert video %s to mp4 format", i)
                    convert_video = "MP4Box " + "-add " + photo_path + "video" + str(i) + ".h264 " + "-new " + mp4_path + "video" + str(i) + ".mp4 "
                    try:
                        output = subprocess.run(convert_video, shell=True)
                    except subprocess.CalledProcessError as e:
                        logger.info ('FAIL:\ncmd:{}\output:{}'.format(e.cmd, e.output))
                    logger.info (" video%s converted to mp4 format", i)
                    logger.info (" video%s is now complete", i)
                logger.info ("========    Finished   =======")
                logger.info ("==============================")
                #break
        #--------------------------------------------------------------#
        # end if this
        #--------------------------------------------------------------#
if __name__ == "__main__":
    main()
