#!/usr/bin/python3 -u
# stored at: /usr/lib/cgi-bin
# sudo setfacl -d -m g::rwx /var/www/html
# sudo setfacl -d -m g::rwx /var/www/html/images
#--------------------------------------------------------------------#")
# This program triggers the signal and lamps, and records a video of #")
# the start from the 5 minutes signal to 2 minutes after the start.  #")
# Several (7) videos are at the assumed finish                       #")
#--------------------------------------------------------------------#")
# There is a jumper on the relay board, called COM, jumper on means  #")
# COM is set to ground, this means that when state = High it sets    #")
# relay to ON.                                                       #")
#--------------------------------------------------------------------#")
# If the pin is connected to GND, the system does a shutdown, not OK #")
#--------------------------------------------------------------------#")
import os, sys
start_time = str(sys.argv[1])
week_day = str(sys.argv[2])
video_delay = int(sys.argv[3])
num_videos = int(sys.argv[4])
video_dur = int(sys.argv[5])
import time
import logging
import logging.config
logging.config.fileConfig('logging.conf')
from datetime import date
from datetime import datetime
import datetime as dt
logger = logging.getLogger('Start')     # create logger
logger.info (" Start logging")
import subprocess
import picamera
photo_path = '/var/www/html/images/'
dropbox_path = '/usr/lib/cgi-bin/dropbox_uploader.sh upload ' + photo_path
photo_name = 'latest.jpg'
##########
string=$(/opt/vc/bin/vcgencmd get_camera)
substring="detected=1"
if test "${string#*$substring}" != "$string"
then
    logger.info ("camera detected")
    camera = picamera.PiCamera()
    camera.resolution = (1280, 720)
    #camera.brightness = 70
    #camera.hflip = True
    #camera.vflip = True
    camera.rotation = (180) # Depends on how camera is mounted
    #---------------------------------------------------------#
    # Video made with different frame-rates, with 640,480:
    #  - 30 fps gives for 1 hour video 225 Mbyte
    #  - 10 fps gives for 1 hour video  76 Mbyte
    #  - 5 fps gives for 1 hour video   50 Mbyte
    #---------------------------------------------------------#
    camera.framerate = 5
    #---------------------------------------------------------#
else
    logger.info ("camera NOT detected")    # Camera not connected.
fi

##########

# set up the GPIO channels - one for output "signal"
# one as output for "lamp1" and one for "lamp2"
#--------------------------------------------------------------#
import RPi.GPIO as GPIO
# using BCM GPIO 00..nn numbers
# GPIO19 =  pin 35 left 3rd from the bottom, for signalhorn
# GPIO20 = pin 38 right 2nd from the bottom, for lamp1
# GPIO26 = pin 37 left 2nd from the bottom, for lamp2
# GPIO21 = pin 40 right 1th from bottom
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(True)
signal = 19 # GPI019 = pin 35 // U1
lamp1 = 20  # GPIO20 = pin 38 // U2
lamp2 = 26  # GPIO26 = pin 37 // U3
# lamp3 = 21 # GPIO21 = pin 40 // U44 # not used
#
# ON & OFF can be set to LOW or HIGH depending on whatrelay type is used
ON = GPIO.HIGH
OFF = GPIO.LOW
GPIO.setup(signal, GPIO.OUT, initial=OFF)
GPIO.setup(lamp1,  GPIO.OUT, initial=OFF)
GPIO.setup(lamp2,  GPIO.OUT, initial=OFF)
#---------------------------------------------------------------#
signal_duration = 1 # 1 sec
#---------------------------------------------------------------#
logger.info (" Start_time = %s", start_time)
start_hour, start_minute = start_time.split(':')
start_time_sec = 60 * (int(start_minute) + 60 * int(start_hour)) # 6660
logger.info (' Weekday = %s', week_day)
#logger.info (" Time ok, now waiting to 5 minutes before start %d", start_time)
#logger.info (" Video_delay = ", video_delay, "video_dur = ", video_dur)
#---------------------------------------------------#
# remove video0.mp4 .. video7.mp
# sudo chmod a+w filename-or-full-filepath
#---------------------------------------------------#
remove_video = "rm " + photo_path + "video*.*4"
#subprocess.Popen([remove_video], shell = True)
try:
    subprocess.Popen([remove_video], shell = True)
    #os.remove("remove_video")
except OSError:
    logger.info (" OS error remove video*.*4 ")
    pass
#---------------------------------------------------#
# While loop
#---------------------------------------------------#
while ( True ):
    try:
        now = dt.datetime.now()
        wd = dt.datetime.today().strftime("%A")
        #-----------------------------------------------------------#
        # startday = "Wednesday" = "wd" = 3
        #-----------------------------------------------------------#
        if wd == week_day :            # example Wednesday = 3
            #-------------------------------------------------------#
            # Define start for regatta and time for finish video and
            # duration for each Video defined with minutes after start
            #-------------------------------------------------------#
            # setup start time
            #-------------------------------------------------------#
            t = dt.datetime.now() # ex: 2015-01-04 18:48:33.255145
            time_now = t.strftime('%H:%M:%S')   # 18:48:33
            nh, nm, ns = time_now.split(':')
            seconds_now =  60 * (int(nm) + 60 * int(nh)) + int(ns)
            # seconds now is 60*(min + 60*hours)+seconds
            #-------------------------------------------------------#
            #
            #    Varningssignal === 5 minute signal before start
            #
            #-------------------------------------------------------#
            camera.annotate_background = True
            camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if seconds_now == (start_time_sec - 5*60) :
                logger.info ("== Executing today, daynumber = ", wd)
                #---------------------------------------------------------#
                #
                # trigger video0 recording 5 min before until 2 min after start
                #
                #---------------------------------------------------------#
                camera.start_recording(photo_path + "video0.h264")
                time.sleep(1)
                #---------------------------------------------------------#
                # trigger signal and lamp
                #---------------------------------------------------------#
                logger.info (" Varningsignal 5 minutes before start (1 sec)")
                GPIO.output(signal, ON)  # Signal On
                time.sleep(0.5)
                #--------------------------------------------------------#
                # 5 min before start, picture with overlay of date & time
                #--------------------------------------------------------#
                camera.annotate_background = True
                camera.annotate_text = "5 min  " + dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                camera.capture(photo_path + "1st-5min_pict.jpg", use_video_port=True)
                time.sleep(0.5)                 # 1 sec
                GPIO.output(signal, OFF)  # Signal Off
                time.sleep(2)             # 1 sec
                GPIO.output(lamp1, ON)    # Lamp1 On (Flag O)
                logger.info (" 5 min Lamp-1 On -- Up with Flag O")
            #----------------------------------------------------------#
            # $$$$  Forberedelsesignal 4 minutes
            #----------------------------------------------------------#
            if seconds_now == (start_time_sec - 4*60 - 1):
                logger.info (" Prep-signal 4 min before start, for 1 sec")
                GPIO.output(signal, ON)   # Signal On
                time.sleep(0.8)           # 0.8 sec
                GPIO.output(signal, OFF)  # Signal Off
                #------------------------------------------------------#
                # 4 min before start, picture with overlay of date & time
                #------------------------------------------------------#
                # camera.annotate_background = True
                time.sleep(0.5)           # 0.5 sec
                camera.annotate_text = "4 min  " + dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                camera.capture(photo_path + "1st-4min_pict.jpg", use_video_port=True)
                time.sleep(2)             # 2 sec
                GPIO.output(lamp2, ON)    # Lamp 2 On (Flag P)
                logger.info (" 4 min Lamp-2 On  --- Up with Flag P ")
            #----------------------------------------------------------#
            # $$$$ One-Minute-to-start signal
            #----------------------------------------------------------#
            if seconds_now == (start_time_sec - 1*60):
                logger.info (" 1 minute before start, signal on for 1 sec")
                GPIO.output(signal, ON)  # Signal On
                time.sleep(0.5)          # 0.5 sec
                GPIO.output(signal, OFF) # Signal Off
                time.sleep(0.5)          # 0.5 sec
                #------------------------------------------------------#
                # 1 min before start picture with overlay of date & time
                #------------------------------------------------------#
                camera.annotate_text = "1 min  " + dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                camera.capture(photo_path + "1st-1min_pict.jpg", use_video_port=True)
                time.sleep(2)              # 1 sec
                GPIO.output(lamp2, OFF)    # Lamp 2 Off (Flag P)
                logger.info (" 1 min  Lamp-2 Off -- Flag P down")
            #----------------------------------------------------------#
            #$$$$ Start signal
            #----------------------------------------------------------#
            if seconds_now == start_time_sec :
                s_start = time.time()  # will be used for annotations of seconds
                logger.info(" Start signal on for 1 sec ")
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
                GPIO.output(signal, ON)  # Signal On
                time.sleep(0.8)
                GPIO.output(signal, OFF)   # Signal Off
                time.sleep(0.5)            # 0.5 sec
                #-------------------------------------------------------#
                # start picture with overlay of date & time
                #-------------------------------------------------------#
                camera.annotate_text = "Start " + dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                camera.capture(photo_path + "1st-start_pict.jpg", use_video_port=True)
                time.sleep(2)              # 1 sec
                GPIO.output(lamp1, OFF)    # Lamp 1 Off (Flag O)
                logger.info(" Start -- Lamp-1 Off  --- Flag O down")
                #------------------------------------------------------#
                # continue  video0 recording for 2 minutes after Start
                #------------------------------------------------------#
                logger.info (" Wait 2 minutes then stop video recording")
                while (dt.datetime.now() - t).seconds < 118:
                    camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    camera.wait_recording(1)
                #------------------------------------------------------#
                # stop video0 recording
                #------------------------------------------------------#
                camera.stop_recording()
                logger.info (" video 0 recording stopped")
                time.sleep(2)             # delay 2 sec
                #------------------------------------------------------#
                # convert video0 format from h264 to mp4
                #------------------------------------------------------#
                logger.info (" >>>>>> start convert video 0 to mp4 format")
                from subprocess import CalledProcessError
                convert_video = "MP4Box -add " + photo_path + "video0.h264 " + photo_path + "video0.mp4 "
#---------------------------------------------------------------------------------------#
# https://stackoverflow.com/questions/45040261/python-3-auto-conversion-from-h264-to-mp4
#---------------------------------------------------------------------------------------#
                try:
                    output = subprocess.check_output(convert_video, stderr=subprocess.STDOUT, shell=True)
                except subprocess.CalledProcessError as e:
                    logger.info ('FAIL:\ncmd:{}\noutput:{}'.format(e.cmd, e.output))
                #logger.info (" >>>>>>>>> innan communicate")
                #proc.communicate()
                #sys.stdout.flush()
                logger.info (" video 0 converted to mp4 format")
                #------------------------------------------------------#
                # Send pictures to DB
                #------------------------------------------------------#
                send_to_DB = dropbox_path + "*pict.jpg " + "/"
                proc = subprocess.Popen ([send_to_DB], shell = True)
                logger.info (" All pict.jpg sent to dropbox")
                #------------------------------------------------------#
                # send video0 to DROPBOX
                #------------------------------------------------------#
                logger.info (" start send video0 to dropbox")
                send_to_DB = dropbox_path + "video0.mp4 " + "/"
                proc = subprocess.Popen ([send_to_DB], shell = True)
                logger.info (" video0 sent to dropbox")
                #----------------------------------------------------------#
                # Wait for finish, when next video1 will start, video_delay
                #----------------------------------------------------------#
                t = dt.datetime.now()
                logger.info (" Time now: %s", t.strftime('%H:%M:%S'))
                sum = video_delay - 2  # Delay in minutes
                while sum > 0:
                        sum = sum - 1
                        time.sleep(60)
                #        logger.info (" video_delay %s", sum ,"in minutes" )
                        logger.info (' sum: %s', sum)
                #----------------------------------------------------------#
                # end while loop, delay from 2 minutes after start to video1
                #----------------------------------------------------------#
                # Result video, duration at "video_dur"
                #----------------------------------------------------------#
                logger.info (" num_videos = %s",num_videos)
                logger.info (' video duration = %s', video_dur)
                for i in range(1, num_videos + 1):
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
                logger.info (" This was the last Video =====")
                logger.info ("==============================")
                for i in range(1, num_videos + 1):
                        logger.info (' i = %s', i)
                        t = dt.datetime.now()
                        logger.info (" Time now: %s", t.strftime('%H:%M:%S'))
                        # Camera running convert previous made video #
                        logger.info (' convert video%s', i, "  to mp4 format")
                        convert_video = "MP4Box -add " + photo_path + "video" + str(i) + ".h264 " + photo_path + "video" + str(i) +".mp4"
                        try:
                            output = subprocess.check_output(convert_video, stderr=subprocess.STDOUT, shell=True)
                        except subprocess.CalledProcessError as e:
                            logger.info ('FAIL:\ncmd:{}\output:{}'.format(e.cmd, e.output))
                        logger.info (' video%s', i ," converted to mp4 format")
                        logger.info (' video%s', i ,' is now complete !!! Time now: %s', dt.datetime.now().strftime('%H:%M:%S'))
                        #------------------------------------------------------#
                        # send Video to DROPBOX
                        #------------------------------------------------------#
                        logger.info (" send video%s", i ," to dropbox")
                        send_to_DB = dropbox_path + "video" + str(i) + ".mp4 " + "/"
                        proc = subprocess.Popen ([send_to_DB], shell = True)
                        logger.info (' video%s', i ," sent to dropbox")
                logger.info ("========    Finished   =======")
                logger.info ("==============================")
                GPIO.cleanup()
                break
    #--------------------------------------------------------------#
    # end if this Weekday
    #--------------------------------------------------------------#
    except KeyboardInterrupt:
        logger.info ("======= Stopped by Ctrl-C =====")
        break
    except IOError as e:
        logger.warn ("I/O error({0}): {1}".format(e.errno, e.strerror))
    except ValueError:
        logger.warn ("Could not convert data to an integer.")
    except RuntimeError:
        logger.warn ("Runtime error")
GPIO.cleanup()
