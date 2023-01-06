"""
Common constants and tools between blender-specific modules
"""

import pathlib
import os
import os.path

"""
Addon info

HACK Blender only parses the AST for bl_info so we can't just define it here if it's
not already cached, which it isn't for new installs
"""
import dummy

# Get the path
BLENDER_TOOLS_PATH = os.path.abspath(dummy.__file__)[:-8]

# Read main file
BL_INFO = pathlib.Path(BLENDER_TOOLS_PATH + "/blender_tools.py").read_text()

# Get the stuff
# NOTE Breaks if we ever have { or } in bl_info
BL_INFO = eval(BL_INFO[BL_INFO.index("{"):BL_INFO.index("}") + 1])

"""
Max length for property strings
"""
MAX_STRING_LENGTH = 512

"""
Update info URL
"""
UPDATE_INFO = "https://smashing-tech.github.io/Smash-Hit-Blender-Tools/update.json"

"""
Enable logging
"""
PRINT_LOGGING = True
FILE_LOGGING = False

"""
Blender Tools configuration directory
"""
HOME_FOLDER = str(pathlib.Path.home())
TOOLS_HOME_FOLDER = HOME_FOLDER + "/Smash Hit Blender Tools"

# Create shbt folder if it does not exist
os.makedirs(TOOLS_HOME_FOLDER, exist_ok = True)
