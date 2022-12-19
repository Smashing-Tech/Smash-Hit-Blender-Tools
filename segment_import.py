"""
Smash Hit Blender Tools segment import
"""

import common
import xml.etree.ElementTree as et
import bpy
import gzip

## IMPORT
## The following things are related to the importer, which is not complete.

def removeEverythingEqualTo(array, value):
	"""
	Remove everything in an array equal to a value
	"""
	
	while (True):
		try:
			array.remove(value)
		except ValueError:
			return array

def sh_add_box(pos, size):
	"""
	Add a box to the scene and return reference to it
	
	See: https://blender.stackexchange.com/questions/2285/how-to-get-reference-to-objects-added-by-an-operator
	"""
	
	bpy.ops.mesh.primitive_cube_add(size = 1.0, location = (pos[0], pos[1], pos[2]), scale = (size[0] * 2, size[1] * 2, size[2] * 2))
	
	return bpy.context.active_object

def sh_add_empty():
	"""
	Add an empty object and return a reference to it
	"""
	
	o = bpy.data.objects.new("empty", None)
	
	bpy.context.scene.collection.objects.link(o)
	
	o.empty_display_size = 1
	o.empty_display_type = "PLAIN_AXES"
	
	return o

def sh_import_modes(s):
	"""
	Import a mode string
	"""
	
	mask = int(s)
	res = set()
	
	for v in [("training", 1), ("classic", 2), ("expert", 4), ("zen", 8), ("versus", 16), ("coop", 32)]:
		if ((mask & v[1]) == v[1]):
			res.add(v[0])
	
	return res

def sh_parse_tile(s):
	"""
	Parse tile strings
	"""
	
	string = s.split(" ")
	final = []
	
	for i in range(len(string)):
		final.append(max(min(int(string[i]), 63), 0))
	
	return final

def sh_parse_tile_size(s):
	"""
	Parse tile strings
	"""
	
	string = s.split(" ")
	final = []
	
	for i in range(len(string)):
		final.append(float(string[i]))
	
	return final

def sh_parse_colour(s):
	"""
	Parse colour strings
	"""
	
	a = removeEverythingEqualTo(s.split(" "), "")
	
	# Remove remaining space strings
	a = [i for i in a if i != " "]
	
	if (len(a) < 9):
		return [(float(a[0]), float(a[1]), float(a[2]))]
	else:
		return [(float(a[0]), float(a[1]), float(a[2])), (float(a[3]), float(a[4]), float(a[5])), (float(a[6]), float(a[7]), float(a[8]))]

def show_message(title = "Info", message = "", icon = "INFO"):
	"""
	Show a message as a popup
	"""
	
	def draw(self, context):
		self.layout.label(text = message)
	
	bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)
	
def sh_import_segment(fp, context, compressed = False):
	"""
	Load a Smash Hit segment into blender
	"""
	
	root = None
	
	if (not compressed):
		with open(fp, "r") as f:
			root = f.read()
	else:
		with gzip.open(fp, "rb") as f:
			root = f.read().decode()
	
	root = et.fromstring(root)
	
	scene = context.scene.sh_properties
	segattr = root.attrib
	
	# Check segment protection and enforce it
	# 
	# These are not designed to stop someone really dedicated from stealing
	# segments, but it should stop someone from casually copying segments.
	drm = segattr.get("drm", None)
	
	if (drm):
		drm = drm.split(" ")
		
		for d in drm:
			if (d == "NoImport"):
				show_message("Import error", "There was an error importing this segment.")
				return {"FINISHED"}
	
	# Segment length
	seg_size = segattr.get("size", "12 10 0").split(" ")
	scene.sh_len = (float(seg_size[0]), float(seg_size[1]), float(seg_size[2]))
	
	# Segment template
	scene.sh_template = segattr.get("template", "")
	
	# Soft shadow
	scene.sh_softshadow = float(segattr.get("softshadow", "-0.0001"))
	
	# Lights
	scene.sh_light_left = float(segattr.get("lightLeft", "1"))
	scene.sh_light_right = float(segattr.get("lightRight", "1"))
	scene.sh_light_top = float(segattr.get("lightTop", "1"))
	scene.sh_light_bottom = float(segattr.get("lightBottom", "1"))
	scene.sh_light_front = float(segattr.get("lightFront", "1"))
	scene.sh_light_back = float(segattr.get("lightBack", "1"))
	
	# ambient, if lighting is enabled
	lighting_ambient = segattr.get("ambient", None)
	
	if (lighting_ambient):
		scene.sh_lighting = True
		scene.sh_lighting_ambient = sh_parse_colour(lighting_ambient)[0]
	else:
		scene.sh_lighting = False
	
	for obj in root:
		kind = obj.tag
		properties = obj.attrib
		
		# Ignore obstacles exported with IMPORT_IGNORE="STONEHACK_IGNORE"
		if (properties.get("IMPORT_IGNORE") == "STONEHACK_IGNORE" or properties.get("type") == "stone"):
			continue
		
		# Object position
		pos = properties.get("pos", "0 0 0").split(" ")
		pos = (float(pos[2]), float(pos[0]), float(pos[1]))
		
		# Object rotation
		rot = properties.get("rot", "0 0 0").split(" ")
		rot = (float(rot[2]), float(rot[0]), float(rot[1]))
		
		# Boxes
		if (kind == "box"):
			# Size for boxes
			size = properties.get("size", "0.5 0.5 0.5").split(" ")
			size = (float(size[2]), float(size[0]), float(size[1]))
			
			# Add the box; zero size boxes are treated as points
			b = None
			if (size[0] <= 0.0 or size[1] <= 0.0 or size[2] <= 0.0):
				b = sh_add_empty()
				b.location = pos
			else:
				b = sh_add_box(pos, size)
			
			# Boxes can (and often do) have templates
			b.sh_properties.sh_template = properties.get("template", "")
			
			# Reflective property
			b.sh_properties.sh_reflective = (properties.get("reflection", "0") == "1")
			
			# visible, colour, tile for boxes
			# NOTE: Tile size and rotation are not supported those are not imported yet
			# NOTE: Extra template logic is here because built-in box baking tools will only
			# inherit visible from template when visible is not set at all, and since
			# it is not possible to tell blender tools to explicitly inherit from
			# a template we need to settle with less than ideal but probably the most
			# intuitive behaviour in order to have box templates work: we do not
			# include visible if there is a template and visible is not set.
			b.sh_properties.sh_visible = (properties.get("visible", "1") == "1" and not b.sh_properties.sh_template)
			
			# NOTE: The older format colorX/Y/Z is no longer supported, should it be readded?
			colour = sh_parse_colour(properties.get("color", "0.5 0.5 0.5"))
			
			if (len(colour) == 1):
				b.sh_properties.sh_tint = (colour[0][0], colour[0][1], colour[0][2], 1.0)
			else:
				b.sh_properties.sh_use_multitint = True
				b.sh_properties.sh_tint1 = (colour[0][0], colour[0][1], colour[0][2], 1.0)
				b.sh_properties.sh_tint2 = (colour[1][0], colour[1][1], colour[1][2], 1.0)
				b.sh_properties.sh_tint3 = (colour[2][0], colour[2][1], colour[2][2], 1.0)
			
			# NOTE: The older format tileX/Y/Z is no longer supported, should it be readded?
			tile = sh_parse_tile(properties.get("tile", "0"))
			
			if (len(tile) == 1):
				b.sh_properties.sh_tile = tile[0]
			else:
				b.sh_properties.sh_use_multitile = True
				b.sh_properties.sh_tile1 = tile[0]
				b.sh_properties.sh_tile2 = tile[1]
				b.sh_properties.sh_tile3 = tile[2]
			
			# Tile size
			tileSize = sh_parse_tile_size(properties.get("tileSize", "1"))
			tileSizeLen = len(tileSize)
			
			# Clever trick to parse the tile sizes; for 1 tilesize this applies
			# to all sides, for 3 tilesize this applies each tilesize to their
			# proper demension. (If there are two, they are assigned "X Y" -> X Y Y
			# but that should never happen)
			for i in range(3):
				b.sh_properties.sh_tilesize[i] = tileSize[min(i, tileSizeLen - 1)]
			
			# TODO: I'm not adding sh_parse_tilerot for now...
			tileRot = sh_parse_tile(properties.get("tileRot", "0"))
			tileRotLen = len(tileRot)
			
			for i in range(3):
				b.sh_properties.sh_tilerot[i] = tileRot[min(i, tileRotLen - 1)] % 4 # HACK: ... so I'm doing this :)
			
			# Glow for lighting
			b.sh_properties.sh_glow = float(properties.get("glow", "0"))
		
		# Obstacles
		elif (kind == "obstacle"):
			# Create obstacle and set pos/rot
			o = sh_add_empty()
			o.location = pos
			o.rotation_euler = rot
			
			# Set type and add the attributes
			o.sh_properties.sh_type = "OBS"
			o.sh_properties.sh_obstacle = properties.get("type", "")
			o.sh_properties.sh_template = properties.get("template", "")
			o.sh_properties.sh_mode = sh_import_modes(properties.get("mode", "63"))
			o.sh_properties.sh_param0 = properties.get("param0", "")
			o.sh_properties.sh_param1 = properties.get("param1", "")
			o.sh_properties.sh_param2 = properties.get("param2", "")
			o.sh_properties.sh_param3 = properties.get("param3", "")
			o.sh_properties.sh_param4 = properties.get("param4", "")
			o.sh_properties.sh_param5 = properties.get("param5", "")
			o.sh_properties.sh_param6 = properties.get("param6", "")
			o.sh_properties.sh_param7 = properties.get("param7", "")
			o.sh_properties.sh_param8 = properties.get("param8", "")
			o.sh_properties.sh_param9 = properties.get("param9", "")
			o.sh_properties.sh_param10 = properties.get("param10", "")
			o.sh_properties.sh_param11 = properties.get("param11", "")
			if (properties.get("hidden", "0") == "1"): o.sh_properties.sh_hidden = True
		
		# Decals
		elif (kind == "decal"):
			# Create obstacle and set pos/rot
			o = sh_add_empty()
			o.location = pos
			o.rotation_euler = rot
			
			# Set type and tile number
			o.sh_properties.sh_type = "DEC"
			o.sh_properties.sh_decal = int(properties.get("tile", "0"))
			
			# Set the colourisation of the decal
			colour = properties.get("color", None)
			if (colour):
				o.sh_properties.sh_havetint = True
				colour = colour.split(" ")
				colour = (float(colour[0]), float(colour[1]), float(colour[2]), float(colour[3]) if len(colour) == 4 else 1.0)
				o.sh_properties.sh_tint = colour
			else:
				o.sh_properties.sh_havetint = False
			
			# Blend mode
			o.sh_properties.sh_blend = float(properties.get("blend", "1"))
			
			# Set the hidden flag
			if (properties.get("hidden", "0") == "1"): o.sh_properties.sh_hidden = True
		
		# Power-ups
		elif (kind == "powerup"):
			# Create obstacle and set pos
			o = sh_add_empty()
			o.location = pos
			
			# Set type and powerup kind
			o.sh_properties.sh_type = "POW"
			o.sh_properties.sh_powerup = properties.get("type", "ballfrenzy")
			
			# Set hidden
			if (properties.get("hidden", "0") == "1"): o.sh_properties.sh_hidden = True
		
		# Water
		elif (kind == "water"):
			# Create obstacle and set pos
			size = properties.get("size", "1 1").split(" ")
			size = (float(size[1]), float(size[0]), 0.0)
			
			o = sh_add_box(pos, size)
			
			# Set the type
			o.sh_properties.sh_type = "WAT"
			
			# Set hidden
			if (properties.get("hidden", "0") == "1"): o.sh_properties.sh_hidden = True
	
	return {"FINISHED"}
