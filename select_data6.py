#!/usr/bin/python3
#Before running program, change mode of file using chmod 755 UNIX command to make file executable.

import cgi
import cgitb

cgitb.enable()  # Enable CGI error reporting

# Print the Content-Type header
print("Content-Type: text/html\n")

# Read user data from the request
import sys
import os
import subprocess

form = cgi.FieldStorage()
# Get data from drop down fields
week_day = form.getvalue('day')
start_time = (form.getvalue('start_time'))
num_video = int(form.getvalue('num_video'))
video_delay = int(form.getvalue('video_delay'))
video_dur = int(form.getvalue('video_dur'))
execution_string =  "python3 " + "regattastart6.py " + str(start_time) + " " + week_day + " " + str(video_delay) + " " + str(num_video) + " " + str(video_dur) + " " + " &"
proc = subprocess.run([execution_string], shell = True)

if week_day:
   print("Content-type:text/html")
   print(f"<html><body>")
   print (f"Start is set to: {start_time}")
   print (f"Number of videos: {num_video}")
   print(f"</body></html>")
else:
    print(f"<html><body>")
    print (f"31 Sorry, we cannot turn your input to numbers.</p>")
    print(f"</body></html>")
