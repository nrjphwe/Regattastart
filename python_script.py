#!/usr/bin/python3
import cgi
import cgitb
cgitb.enable()  # Enable CGI error reporting

# Print the Content-Type header
print("Content-Type: text/html\n")

# Read user data from the session
import os
from http import cookies

print(f"Cookie Data: {os.environ.get('HTTP_COOKIE')}")
print(f"User's Name (from session): {user_name}")
# Process the user data
print(f"<html><body>")
print(f"User's Name: {user_name}")


#Debug:
cookie = cookies.SimpleCookie(os.environ.get("HTTP_COOKIE"))
user_name = cookie.get('user_name').value if 'user_name' in cookie else "Name not set"
print(f"debug_User's Name") 
print(f"</body></html>")
