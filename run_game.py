#!/usr/bin/python
from __future__ import print_function
import webbrowser

URL = 'http://dark-world.mauveweb.co.uk/'

print("The multi-user version of this game is hosted at")
print(URL)

print()
print(
    "You can run your own server by running run_server.py "
    "but it won't be as fun without others..."
)

webbrowser.open(URL)
