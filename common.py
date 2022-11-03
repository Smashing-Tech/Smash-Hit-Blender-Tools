"""
Common constants and tools between blender-specific modules
"""

"""
Addon info
"""
BL_INFO = {
	"name": "Smash Hit Tools",
	"description": "Segment exporter and property editor for Smash Hit",
	"author": "Knot126",
	"version": (2, 0, 14),
	"blender": (3, 2, 0),
	"location": "File > Import/Export and 3D View > Tools",
	"warning": "",
	"wiki_url": "https://github.com/knot126/Smash-Hit-Blender-Tools/wiki",
	"tracker_url": "https://github.com/knot126/Smash-Hit-Blender-Tools/issues",
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
