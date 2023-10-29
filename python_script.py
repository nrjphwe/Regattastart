#!/usr/bin/python3

import cgi
import cgitb

cgitb.enable()  # Enable CGI error reporting

# Print the Content-Type header
print("Content-Type: text/html\n")

# Read user data from the request
import sys
import os

form = cgi.FieldStorage()
user_name = form.getvalue("name")

if user_name:
    print(f"<html><body>")
    print(f"User's Name (from request): {user_name}")
    print(f"</body></html>")
else:
    print(f"<html><body>")
    print("User's Name not provided in the request.")
    print(f"</body></html>")
