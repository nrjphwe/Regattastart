#!/usr/bin/python3 -u
#Before running program, change mode of file using chmod 755 UNIX command to make file executable.
import time, subprocess, sys, os
from http import cookies
# Import modules for CGI handling
import cgi, cgitb,datetime
cgitb.enable(display=0, logdir="/usr/lig/cgi-bin/") #for debugging
# Create instance of FieldStorage
form = cgi.FieldStorage()
# Get data from drop down fields
if form.getvalue('day'):
   week_day = form.getvalue('day')
else:
   week_day = "Wednesday"
"""
Passing cookies between a .cgi and php program
"""
cookme = cookies.SimpleCookie()
cookme.load(os.environ.get('HTTP_COOKIE',''))
##
#cookme = os.environ.get('HTTP_COOKIE')
##
FormData = cgi.FieldStorage()
entered_name=FormData.getvalue('video_delay')
test = 0
#to set a cookie this has to be your first output.
if ('video_delay'or 'video_dur') in FormData:
    cooked = cookies.SimpleCookie()
    cooked['video_delay']=FormData.getvalue('video_delay')
    cooked['video_delay']['path']='/'
    cooked['video_dur']=FormData.getvalue('video_dur')
    cooked['video_dur']['path']='/'
    cooked['num_video']=FormData.getvalue('num_video')
    cooked['num_video']['path']='/'
    test = 1
    print (cooked)
# Get data from fields
print ("Content-type: text/html\r\n\r\n")
print ()
print ("<html>")
print ("<head>")
print ("<title> select_data7.py Regattastart7 sessions </title>")
print ("<body>")
#print ("<meta http-equiv='refresh' content='60; URL=/cgi-bin/select_data7.py'>")
try:
      week_day = (form.getvalue('day'))
      start_time = (form.getvalue('start_time'))
      num_video = int(form.getvalue('num_video'))
      video_delay = int(form.getvalue('video_delay'))
      video_dur = int(form.getvalue('video_dur'))
      print ("<h2> Start is set to : %s ,time: %d:%d</h2>" % (week_day, start_time, num_video, video_delay, video_dur))
except:
      print ("<p>Sorry, we cannot turn your input to numbers.<p/>")
###
if ('video_delay' or 'video_dur') in cookme:
    print ("<h4>Previous or current video_delay:")
    print (cookme.get('video_delay').value)
    print ("Current video_dur:")
    print (cookme.get('video_dur').value)
    print ("Current num_video: ")
    print (cookme.get('num_video').value)
    print ("</h4>")
else:
    print ("<h4>no video_delay/video_dur set yet.</h4>")
if test==1:
    print ("<h4>your cookies have been changed just now.</h4><br/>")
    print ("<h4>new video_delay = ")
    print (FormData.getvalue('video_delay'))
    print ("</h4><h3>new video_dur = ")
    print (FormData.getvalue('video_dur'))
    print ("</h3><br/>")
else:
    print ("No video_delay or video_dur were specified so it is not being changed.<br/>")
print ("<form method=\"post\" action = \"/index7.php\" name='myform1'>")
print ("video_delay: <input name='video_delay' size=3 /><br/>")
print ("video_dur....: <input name='video_dur' size=3 /><br/>")
print ("num_video....: <input name='num_video' size=3 /><br/>")
print ("then we we'll set a cookie and everybody is happy.<br/>")
print ("<input type='submit'/>")
print ("</form>")
print ("<h2> <a href=""/index.php"">  Resultat sida  </a></h2>")
sys.stdout.flush()
os.close(sys.stdout.fileno()) # Break web pipe
if os.fork(): # Get out parent process
   sys.exit()
# Continue with new child process
time.sleep(1)  # Be sure the parent process reach exit command.
os.setsid()
execution_string =  "python3 " + "regattastart7.py " + str(start_time) + " " + str(week_day) + " " + str(video_delay) + " " + str(num_video) + " " + str(video_dur) + " " + " &"
proc = subprocess.Popen([execution_string], shell = True)
proc.communicate()
#print (cookme)
print ("</body>")
print ("</html>")
if os.fork():
  print ("success")
  sys.exit(0)
