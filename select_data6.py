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

form = cgi.FieldStorage()
# Get data from drop down fields
week_day = form.getvalue('day')
start_time = (form.getvalue('start_time'))
num_video = int(form.getvalue('num_video'))
video_delay = int(form.getvalue('video_delay'))
video_dur = int(form.getvalue('video_dur'))

if week_day:
   print(f"<html><body>")
   print (f"Start is set to: {start_time}")
   print(f"</body></html>")
else:
    print(f"<html><body>")
    print (f"31 Sorry, we cannot turn your input to numbers.</p>")
    print(f"</body></html>")
