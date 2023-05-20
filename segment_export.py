"""
Smash Hit Blender Tools segment export
"""

import common
import xml.etree.ElementTree as et
import bpy
import gzip
import os
import os.path as ospath
import pathlib
import tempfile
import bake_mesh
import obstacle_db
import util

from bpy.props import (StringProperty, BoolProperty, IntProperty, IntVectorProperty, FloatProperty, FloatVectorProperty, EnumProperty, PointerProperty)
from bpy.types import (Panel, Menu, Operator, PropertyGroup)

def tryTemplatesPath():
	"""
	Try to get the path of the templates.xml file automatically
	"""
	
	# Search for templates.xml and set path
	path = ""
	
	print("Smash Hit Tools: Trying to find templates from APK Editor Studio ...")
	
	##
	## Templates from APK Editor Studio
	##
	
	try:
		# Get the search path
		search_path = tempfile.gettempdir() + "/apk-editor-studio/apk"
		
		print(f"Smash Hit Tools: Try to search in: \"{search_path}\"")
		
		# Enumerate files
		dirs = os.listdir(search_path)
		
		for d in dirs:
			cand = search_path + "/" + d + "/assets/templates.xml.mp3"
			
			print(f"Smash Hit Tools: Try file: \"{cand}\"")
			
			if ospath.exists(cand):
				path = cand
				break
	except FileNotFoundError:
		print("Smash Hit Tools: No APK Editor Studio folder found.")
	
	##
	## Templates file from home directory
	##
	
	homedir_templates = [common.TOOLS_HOME_FOLDER + "/templates.xml", common.HOME_FOLDER + "/smash-hit-templates.xml"]
	
	for f in homedir_templates:
		if (not path and ospath.exists(f)):
			path = f
	
	print(f"Smash Hit Tools: Got file: \"{path}\"")
	
	return path

class ExportHelper2:
	"""
	Extended from blender's default ExportHelper to fix some bugs.
	"""
	
	filepath: StringProperty(
		name = "File Path",
		description = "Filepath used for exporting the file",
		maxlen = 1024,
		subtype = 'FILE_PATH',
	)
	
	check_existing: BoolProperty(
		name = "Check Existing",
		description = "Check and warn on overwriting existing files",
		default = True,
		options = {'HIDDEN'},
	)
	
	# subclasses can override with decorator
	# True == use ext, False == no ext, None == do nothing.
	check_extension = True
	
	def invoke(self, context, _event):
		if not self.filepath:
			blend_filepath = context.blend_data.filepath
			if not blend_filepath:
				blend_filepath = "untitled"
			else:
				blend_filepath = os.path.splitext(blend_filepath)[0]
			
			self.filepath = blend_filepath + self.filename_ext
		
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def check(self, _context):
		"""
		Custom version of filepath check that fixes issues with two dots in names
		"""
		
		change_ext = False
		
		if self.check_extension is not None and self.check_extension:
			if not self.filepath.endswith(self.filename_ext):
				self.filepath += self.filename_ext
				change_ext = True
		
		return change_ext

## Segment Export
## All of the following is related to exporting segments.

def sh_create_root(scene, params):
	"""
	Creates the main root and returns it
	"""
	
	size = {"X": scene.sh_len[0], "Y": scene.sh_len[1], "Z": scene.sh_len[2]}
	
	# VR Multiply setting
	sh_vrmultiply = params.get("sh_vrmultiply", 1.0)
	
	if (sh_vrmultiply != 1.0):
		size["Z"] = size["Z"] * sh_vrmultiply
	
	# Initial segment properties, like size
	seg_props = {
	   "size": str(size["X"]) + " " + str(size["Y"]) + " " + str(size["Z"])
	}
	
	# Check for the template attrib and set
	if (scene.sh_template):
		seg_props["template"] = scene.sh_template
	
	# Lighting
	# We no longer export lighting info if the template is present since that should
	# be taken care of there.
	if (not scene.sh_template):
		if (scene.sh_light_left != 1.0):   seg_props["lightLeft"] = str(scene.sh_light_left)
		if (scene.sh_light_right != 1.0):  seg_props["lightRight"] = str(scene.sh_light_right)
		if (scene.sh_light_top != 1.0):    seg_props["lightTop"] = str(scene.sh_light_top)
		if (scene.sh_light_bottom != 1.0): seg_props["lightBottom"] = str(scene.sh_light_bottom)
		if (scene.sh_light_front != 1.0):  seg_props["lightFront"] = str(scene.sh_light_front)
		if (scene.sh_light_back != 1.0):   seg_props["lightBack"] = str(scene.sh_light_back)
	
	# Check for softshadow attrib and set
	if (scene.sh_softshadow >= 0.0):
		seg_props["softshadow"] = str(scene.sh_softshadow)
	
	# Add ambient lighting if enabled
	if (scene.sh_lighting):
		seg_props["ambient"] = str(scene.sh_lighting_ambient[0]) + " " + str(scene.sh_lighting_ambient[1]) + " " + str(scene.sh_lighting_ambient[2])
	
	# Add fog colour if not default
	if (scene.sh_fog_colour_bottom[0] != 0.0 or scene.sh_fog_colour_bottom[1] != 0.0 or scene.sh_fog_colour_bottom[2] != 0.0 or scene.sh_fog_colour_top[0] != 1.0 or scene.sh_fog_colour_top[1] != 1.0 or scene.sh_fog_colour_top[2] != 1.0):
		seg_props["fogcolor"] = str(scene.sh_fog_colour_bottom[0]) + " " + str(scene.sh_fog_colour_bottom[1]) + " " + str(scene.sh_fog_colour_bottom[2]) + " " + str(scene.sh_fog_colour_top[0]) + " " + str(scene.sh_fog_colour_top[1]) + " " + str(scene.sh_fog_colour_top[2])
	
	# Music track
	if (scene.sh_music):
		seg_props["qt-music"] = scene.sh_music
	
	# Reverb options
	if (scene.sh_reverb):
		seg_props["qt-reverb"] = scene.sh_reverb
	
	# Particle effect
	if (scene.sh_particles):
		seg_props["qt-particles"] = scene.sh_particles
	
	# Protection
	if (scene.sh_drm_disallow_import):
		seg_props["drm"] = "NoImport"
	
	# Creator information - always exported if available
	creator = bpy.context.preferences.addons["blender_tools"].preferences.creator
	
	if (creator):
		seg_props["shbt-meta-creator"] = creator
	
	# Metadata, if allowed
	if (bpy.context.preferences.addons["blender_tools"].preferences.enable_metadata):
		# Export time
		seg_props["shbt-meta-time"] = hex(util.get_time())[2:]
		
		# Export user trace if the creator wasn't specified
		if (not creator):
			seg_props["shbt-meta-trace"] = util.get_trace()
	
	# Create main root and return it
	level_root = et.Element("segment", seg_props)
	level_root.text = "\n\t"
	
	return level_root

def sh_add_object(level_root, scene, obj, params):
	"""
	This will add an obstacle to level_root
	"""
	
	# These positions are swapped
	position = {"X": obj.location[1], "Y": obj.location[2], "Z": obj.location[0]}
	
	# VR Multiply setting
	sh_vrmultiply = params.get("sh_vrmultiply", 1.0)
	
	if (sh_vrmultiply != 1.0):
		position["Z"] = position["Z"] * sh_vrmultiply
	
	# The only gaurrented to exsist is pos
	properties = {
		"pos": str(position["X"]) + " " + str(position["Y"]) + " " + str(position["Z"]),
	}
	
	# Shorthand for obj.sh_properties.sh_type
	sh_type = obj.sh_properties.sh_type
	
	# Type for obstacles
	if (sh_type == "OBS"):
		properties["type"] = obj.sh_properties.sh_obstacle_chooser if obj.sh_properties.sh_use_chooser else obj.sh_properties.sh_obstacle
	
	# Type for power-ups
	if (sh_type == "POW"):
		properties["type"] = obj.sh_properties.sh_powerup
		
	# Hidden for all types
	if (obj.sh_properties.sh_hidden):
		properties["hidden"] = "1"
	else:
		properties["hidden"] = "0"
	
	# Add size for boxes
	if (sh_type == "BOX"):
		# Again, swapped becuase of Smash Hit's demensions
		size = {"X": obj.dimensions[1] / 2, "Y": obj.dimensions[2] / 2, "Z": obj.dimensions[0] / 2}
		
		# VR Multiply setting
		if (sh_vrmultiply != 1.0 and (abs(size["Z"]) > 2.0)):
			size["Z"] = size["Z"] * sh_vrmultiply
		
		properties["size"] = str(size["X"]) + " " + str(size["Y"]) + " " + str(size["Z"])
	
	# Add rotation paramater if any rotation has been done
	if (sh_type == "OBS" or sh_type == "DEC"):
		if (obj.rotation_euler[1] != 0.0 or obj.rotation_euler[2] != 0.0 or obj.rotation_euler[0] != 0.0):
			properties["rot"] = str(obj.rotation_euler[1]) + " " + str(obj.rotation_euler[2]) + " " + str(obj.rotation_euler[0])
	
	# Add template for all types of objects
	# HACK: We don't export with a template value if the visible attribute is checked. There is a bug somewhere in the meshbaker that I can't fix right now which causes this.
	# NOTE I think it's fixed, but it's still pointless to export the template in this case.
	if (obj.sh_properties.sh_template and ((not obj.sh_properties.sh_visible) or (sh_type != "BOX"))):
		properties["template"] = obj.sh_properties.sh_template
	
	# Add mode appearance tag
	if (sh_type == "OBS"):
		mask = 0b0
		
		for v in [("training", 1), ("classic", 2), ("expert", 4), ("versus", 16), ("coop", 32)]:
			if (v[0] in obj.sh_properties.sh_mode):
				mask |= v[1]
		
		if (mask != 0b110111):
			properties["mode"] = str(mask)
	
	# Add reflection property for boxes if not default
	if (sh_type == "BOX" and obj.sh_properties.sh_reflective):
		properties["reflection"] = "1"
	
	# Add glow property for boxes if not default
	if (sh_type == "BOX" and obj.sh_properties.sh_glow != 0.0):
		properties["glow"] = str(obj.sh_properties.sh_glow)
	
	# Add decal number if this is a decal
	if (sh_type == "DEC"):
		properties["tile"] = str(obj.sh_properties.sh_decal)
	
	# Add decal size if this is a decal (based on sh_size)
	if (sh_type == "DEC"):
		properties["size"] = str(obj.sh_properties.sh_size[0]) + " " + str(obj.sh_properties.sh_size[1])
	
	# Add water size if this is a water (based on physical plane properties)
	if (sh_type == "WAT"):
		size = {"X": obj.dimensions[1] / 2, "Z": obj.dimensions[0] / 2}
		
		properties["size"] = str(size["X"]) + " " + str(size["Z"])
	
	# Set each of the tweleve paramaters if they are needed.
	if (sh_type == "OBS"):
		for i in range(12):
			val = getattr(obj.sh_properties, "sh_param" + str(i))
			
			if (val):
				properties["param" + str(i)] = val
	
	# Set tint for decals
	if (sh_type == "DEC" and obj.sh_properties.sh_havetint):
		properties["color"] = str(obj.sh_properties.sh_tint[0]) + " " + str(obj.sh_properties.sh_tint[1]) + " " + str(obj.sh_properties.sh_tint[2]) + " " + str(obj.sh_properties.sh_tint[3])
	
	# Set blend for decals
	if (sh_type == "DEC" and obj.sh_properties.sh_blend != 1.0):
		properties["blend"] = str(obj.sh_properties.sh_blend)
	
	if (sh_type == "BOX"):
		if (obj.sh_properties.sh_visible):
			properties["visible"] = "1"
		else:
			if (not obj.sh_properties.sh_template):
				properties["visible"] = "0"
	
	# Set tile info for boxes if visible and there is no template specified
	if (sh_type == "BOX" and obj.sh_properties.sh_visible):
		# Depending on if colour per side is selected
		if (not obj.sh_properties.sh_use_multitint):
			properties["color"] = str(obj.sh_properties.sh_tint[0]) + " " + str(obj.sh_properties.sh_tint[1]) + " " + str(obj.sh_properties.sh_tint[2])
		else:
			properties["color"] = str(obj.sh_properties.sh_tint1[0]) + " " + str(obj.sh_properties.sh_tint1[1]) + " " + str(obj.sh_properties.sh_tint1[2]) + " " + str(obj.sh_properties.sh_tint2[0]) + " " + str(obj.sh_properties.sh_tint2[1]) + " " + str(obj.sh_properties.sh_tint2[2]) + " " + str(obj.sh_properties.sh_tint3[0]) + " " + str(obj.sh_properties.sh_tint3[1]) + " " + str(obj.sh_properties.sh_tint3[2])
		
		# Depnding on if tile per side is selected
		if (not obj.sh_properties.sh_use_multitile):
			properties["tile"] = str(obj.sh_properties.sh_tile)
		else:
			properties["tile"] = str(obj.sh_properties.sh_tile1) + " " + str(obj.sh_properties.sh_tile2) + " " + str(obj.sh_properties.sh_tile3)
		
		# Tile size for boxes
		if (obj.sh_properties.sh_tilesize[0] != 1.0 or obj.sh_properties.sh_tilesize[1] != 1.0 or obj.sh_properties.sh_tilesize[2] != 1.0):
			properties["tileSize"] = str(obj.sh_properties.sh_tilesize[0]) + " " + str(obj.sh_properties.sh_tilesize[1]) + " " + str(obj.sh_properties.sh_tilesize[2])
		
		# Tile rotation
		if (obj.sh_properties.sh_tilerot[1] > 0.0 or obj.sh_properties.sh_tilerot[2] > 0.0 or obj.sh_properties.sh_tilerot[0] > 0.0):
			properties["tileRot"] = str(obj.sh_properties.sh_tilerot[0]) + " " + str(obj.sh_properties.sh_tilerot[1]) + " " + str(obj.sh_properties.sh_tilerot[2])
	
	# Set the tag name
	element_type = "entity"
	
	if (sh_type == "BOX"):
		element_type = "box"
	elif (sh_type == "OBS"):
		element_type = "obstacle"
	elif (sh_type == "DEC"):
		element_type = "decal"
	elif (sh_type == "POW"):
		element_type = "powerup"
	elif (sh_type == "WAT"):
		element_type = "water"
	
	# Add the element to the document
	el = et.SubElement(level_root, element_type, properties)
	el.tail = "\n\t"
	if (params["isLast"]): # Fixes the issues with the last line of the file
		el.tail = "\n"
	
	if (params.get("sh_box_bake_mode", "Mesh") == "StoneHack" and sh_type == "BOX" and obj.sh_properties.sh_visible):
		"""
		Export a fake obstacle that will represent stone in the level.
		"""
		
		el.tail = "\n\t\t"
		
		size = {"X": obj.dimensions[1] / 2, "Y": obj.dimensions[2] / 2, "Z": obj.dimensions[0] / 2}
		position = {"X": obj.location[1], "Y": obj.location[2], "Z": obj.location[0]}
		
		# VR Multiply setting
		if (sh_vrmultiply != 1.0):
			position["Z"] = position["Z"] * sh_vrmultiply
		
		if (sh_vrmultiply != 1.0 and ((scene.sh_len[2] / 2) - 0.5) < abs(size["Z"])):
			size["Z"] = size["Z"] * sh_vrmultiply
		
		properties = {
			"pos": str(position["X"]) + " " + str(position["Y"]) + " " + str(position["Z"]),
			"type": "stone",
			"param9": "sizeX=" + str(size["X"]),
			"param10": "sizeY=" + str(size["Y"]),
			"param11": "sizeZ=" + str(size["Z"]),
			"IMPORT_IGNORE": "STONEHACK_IGNORE",
		}
		
		if (obj.sh_properties.sh_template):
			properties["template"] = obj.sh_properties.sh_template
		else:
			properties["param7"] = "tile=" + str(obj.sh_properties.sh_decal)
			properties["param8"] = "color=" + str(obj.sh_properties.sh_tint[0]) + " " + str(obj.sh_properties.sh_tint[1]) + " " + str(obj.sh_properties.sh_tint[2])
		
		el_stone = et.SubElement(level_root, "obstacle", properties)
		el_stone.tail = "\n\t"
		if (params["isLast"]):
			el_stone.tail = "\n"

def createSegmentText(context, params):
	"""
	Export the XML part of a segment to a string
	"""
	
	scene = context.scene.sh_properties
	b_scene = context.scene
	level_root = sh_create_root(scene, params)
	
	# Export each object to XML node
	for i in range(len(bpy.data.objects)):
		obj = bpy.data.objects[i]
		
		if (not obj.sh_properties.sh_export):
			continue
		
		params["isLast"] = False
		
		# HACK: This hack doesn't work if the last object isn't visible.
		if (i == (len(bpy.data.objects) - 1)):
			params["isLast"] = True
		
		sh_add_object(level_root, scene, obj, params)
	
	# Add file header with version
	file_header = "<!-- Exporter: Smash Hit Tools v" + str(common.BL_INFO["version"][0]) + "." + str(common.BL_INFO["version"][1]) + "." + str(common.BL_INFO["version"][2]) + " -->\n"
	
	# Get final string
	content = file_header + et.tostring(level_root, encoding = "unicode")
	
	return content

def parseTemplatesXml(path):
	"""
	Load templates from a file
	"""
	
	result = {}
	
	tree = et.parse(path)
	root = tree.getroot()
	
	assert("templates" == root.tag)
	
	# Loop over templates in XML file and load them
	for child in root:
		assert("template" == child.tag)
		
		name = child.attrib["name"]
		attribs = child[0].attrib
		
		result[name] = attribs
	
	return result

def solveTemplates(segment_text, templates = {}):
	"""
	Resolve the templates
	"""
	
	# Load document
	root = et.fromstring(segment_text)
	
	# For each element
	for e in root:
		# Get the template property if it exists
		template = e.attrib.get("template", None)
		
		# If the template exists then we combine
		if (template):
			# This takes the templates, puts them in a dict, then overwrites
			# anything in that dict with what is in the attributes.
			# http://stackoverflow.com/questions/38987/ddg#26853961
			e.attrib = {**templates[template], **e.attrib}
	
	# Back to a string!
	return et.tostring(root)

def MB_progress_update_callback(value):
	bpy.context.window_manager.progress_update(value)

def sh_export_segment(filepath, context, *, compress = False, params = {}):
	"""
	This function exports the blender scene to a Smash Hit compatible XML file.
	"""
	
	# Set wait cursor
	context.window.cursor_set('WAIT')
	
	# If the filepath is None, then find it from the apk and force enable
	# compression
	if (filepath == None and params.get("auto_find_filepath", False)):
		props = context.scene.sh_properties
		
		filepath = util.find_apk()
		
		if (not filepath):
			raise FileNotFoundError("There is currently no APK open in APK Editor Studio. Please open a Smash Hit APK with a valid structure and try again.")
		
		if (not props.sh_level or not props.sh_room or not props.sh_segment):
			raise FileNotFoundError("You have not set one of the level, room or segment name properties needed to use auto export to apk feature. Please set these in the scene tab and try again.")
		
		filepath += "/segments/" + props.sh_level + "/" + props.sh_room + "/" + props.sh_segment + ".xml.gz.mp3"
		
		util.prepare_folders(filepath)
		
		compress = True
	
	# Export to xml string
	content = createSegmentText(context, params)
	
	# Binary segments
	if (params.get("binary", False)):
		import binaryxml
		
		content = binaryxml.from_string(content)
		
		with open(filepath, "wb") as f:
			f.write(content)
		
		return {'FINISHED'}
	
	##
	## Handle test server mode
	##
	
	# TODO: Split into function exportSegmentTest
	if (params.get("sh_test_server", False) == True):
		# Get templates path
		templates = params.get("sh_meshbake_template", None)
		
		# Solve templates if we have them
		if (templates):
			content = solveTemplates(content, parseTemplatesXml(templates))
		
		# Make dirs
		tempdir = tempfile.gettempdir() + "/shbt-testserver"
		os.makedirs(tempdir, exist_ok = True)
		
		# Delete old mesh file
		if (ospath.exists(tempdir + "/segment.mesh")):
			os.remove(tempdir + "/segment.mesh")
		
		context.window_manager.progress_begin(0.0, 1.0)
		
		# Write mesh if needed
		if (params.get("sh_box_bake_mode", "Mesh") == "Mesh"):
			bake_mesh.BAKE_UNSEEN_FACES = params.get("bake_menu_segment", False)
			bake_mesh.ABMIENT_OCCLUSION_ENABLED = params.get("bake_vertex_light", True)
			bake_mesh.LIGHTING_ENABLED = params.get("lighting_enabled", False)
			bake_mesh.bakeMeshToFile(content, tempdir + "/segment.mesh", templates, bake_mesh.BakeProgressInfo(MB_progress_update_callback))
		
		context.window_manager.progress_end()
		
		# Write XML
		with open(tempdir + "/segment.xml", "w") as f:
			f.write(content)
		
		context.window.cursor_set('DEFAULT')
		
		return {'FINISHED'}
	
	##
	## Write the file
	##
	
	# TODO: Split into function exportSegmentNormal
	
	# Cook the mesh if we need to
	if (params.get("sh_box_bake_mode", "Mesh") == "Mesh"):
		# Find file name
		meshfile = ospath.splitext(ospath.splitext(filepath)[0])[0]
		if (compress):
			meshfile = ospath.splitext(meshfile)[0]
		meshfile += ".mesh.mp3"
		
		# Set properties
		# (TODO: maybe this should be passed to the function instead of just setting global vars?)
		bake_mesh.BAKE_UNSEEN_FACES = params.get("bake_menu_segment", False)
		bake_mesh.ABMIENT_OCCLUSION_ENABLED = params.get("bake_vertex_light", True)
		bake_mesh.LIGHTING_ENABLED = params.get("lighting_enabled", False)
		
		# Bake mesh
		bake_mesh.bakeMeshToFile(content, meshfile, (params["sh_meshbake_template"] if params["sh_meshbake_template"] else None), bake_mesh.BakeProgressInfo(MB_progress_update_callback))
	
	context.window_manager.progress_update(0.8)
	
	# Write out file
	if (not compress):
		with open(filepath, "w") as f:
			f.write(content)
	else:
		with gzip.open(filepath, "wb") as f:
			f.write(content.encode())
	
	context.window_manager.progress_update(1.0)
	context.window_manager.progress_end()
	context.window.cursor_set('DEFAULT')
	
	return {"FINISHED"}
