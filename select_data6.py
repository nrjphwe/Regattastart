#!/usr/bin/python3
#Before running program, change mode of file using chmod 755 UNIX command to make file executable.

import cgi
import cgitb
import json

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

# Check for None values and convert to the appropriate types
if not (week_day and start_time and num_video and video_delay and video_dur):
    print("<html><body>")
    print("Error: Some fields are missing.")
    print("</body></html>")
else:
   try:
      start_time = str(start_time)
      num_video = int(num_video)
      video_delay = int(video_delay)
      video_dur = int(video_dur)
      execution_string = (
         "python3 "
         "regattastart6.py "
         f"{start_time} {week_day} {video_delay} {num_video} {video_dur} &"
         )
        proc = subprocess.run([execution_string], shell=True)
   # Process the form data
   # ...
   # Send a response back to index6.php
   response = {"message": "Data processed successfully"}
        print("Content-Type: application/json")
        print()
        print(json.dumps(response))
    except ValueError:
        print("<html><body>")
        print("Error: Some fields contain invalid values.")
        print("</body></html>")
