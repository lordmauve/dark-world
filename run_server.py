"""Server for The Dark World game."""
import sys

if sys.version_info < (3, 6):
    sys.exit("The Dark World requires Python 3.6 or later.")

from darkworld.serve import run_server

run_server(port=8000)
