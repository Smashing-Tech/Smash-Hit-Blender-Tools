"""
Common constants and tools between blender-specific modules
"""
import pathlib
import os

"""
Addon info
"""
BL_INFO = {
	"name": "Smash Hit Tools",
	"description": "Segment exporter and property editor for Smash Hit",
	"author": "Smashing Tech",
	"version": (2, 0, 15),
	"blender": (3, 2, 0),
	"location": "File > Import/Export and 3D View > Tools",
	"warning": "",
	"wiki_url": "https://github.com/Smashing-Tech/Smash-Hit-Blender-Tools/wiki",
	"tracker_url": "https://github.com/Smashing-Tech/Smash-Hit-Blender-Tools/issues",
	"category": "Development",
}

"""
Max length for property strings
"""
MAX_STRING_LENGTH = 512

"""
Updater release channel
"""
CHANNEL = "prerelease"

"""
Update info URL
"""
UPDATE_INFO = "https://smashing-tech.github.io/Smash-Hit-Blender-Tools/update.json"

"""
Enable logging
"""
PRINT_LOGGING = (CHANNEL != "stable")
FILE_LOGGING = False

"""
Blender Tools configuration directory
"""
HOME_FOLDER = str(pathlib.Path.home())
TOOLS_HOME_FOLDER = HOME_FOLDER + "/Smash Hit Blender Tools"

# Create shbt folder if it does not exist
os.makedirs(TOOLS_HOME_FOLDER, exist_ok = True)
