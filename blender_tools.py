"""
Smash Hit segment export tool for Blender
"""

SH_MAX_STR_LEN = 512

bl_info = {
	"name": "Smash Hit Tools",
	"description": "Segment exporter and property editor for Smash Hit",
	"author": "Knot126",
	"version": (2, 0, 8),
	"blender": (3, 0, 0),
	"location": "File > Import/Export and 3D View > Tools",
	"warning": "",
	"wiki_url": "https://github.com/knot126/Smash-Hit-Blender-Tools/wiki",
	"tracker_url": "https://github.com/knot126/Smash-Hit-Blender-Tools/issues",
	"category": "Development",
}

import xml.etree.ElementTree as et
import bpy
import bpy_extras
import gzip
import json
import os
import os.path as ospath
import pathlib
import tempfile
import importlib.util as imut
import bake_mesh
import obstacle_db
import server

from bpy.props import (StringProperty, BoolProperty, IntProperty, IntVectorProperty, FloatProperty, FloatVectorProperty, EnumProperty, PointerProperty)
from bpy.types import (Panel, Menu, Operator, PropertyGroup)

# The name of the test server. If set to false initially, the test server will
# be disabled.
g_process_test_server = True

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
	
	# Lighting
	if (scene.sh_light_left != 1.0):   seg_props["lightLeft"] = str(scene.sh_light_left)
	if (scene.sh_light_right != 1.0):  seg_props["lightRight"] = str(scene.sh_light_right)
	if (scene.sh_light_top != 1.0):    seg_props["lightTop"] = str(scene.sh_light_top)
	if (scene.sh_light_bottom != 1.0): seg_props["lightBottom"] = str(scene.sh_light_bottom)
	if (scene.sh_light_front != 1.0):  seg_props["lightFront"] = str(scene.sh_light_front)
	if (scene.sh_light_back != 1.0):   seg_props["lightBack"] = str(scene.sh_light_back)
	
	# Check for the template attrib and set
	if (scene.sh_template):
		seg_props["template"] = scene.sh_template
	
	# Check for softshadow attrib and set
	if (scene.sh_softshadow >= 0.0):
		seg_props["softshadow"] = str(scene.sh_softshadow)
	
	# Add ambient lighting if enabled
	if (scene.sh_lighting):
		seg_props["ambient"] = str(scene.sh_lighting_ambient[0]) + " " + str(scene.sh_lighting_ambient[1]) + " " + str(scene.sh_lighting_ambient[2])
	
	# Add fog colour if not default
	if (scene.sh_fog_colour_bottom[0] != 0.0 or scene.sh_fog_colour_bottom[1] != 0.0 or scene.sh_fog_colour_bottom[2] != 0.0 or scene.sh_fog_colour_top[0] != 1.0 or scene.sh_fog_colour_top[1] != 1.0 or scene.sh_fog_colour_top[2] != 1.0):
		seg_props["fogcolor"] = str(scene.sh_fog_colour_bottom[0]) + " " + str(scene.sh_fog_colour_bottom[1]) + " " + str(scene.sh_fog_colour_bottom[2]) + " " + str(scene.sh_fog_colour_top[0]) + " " + str(scene.sh_fog_colour_top[1]) + " " + str(scene.sh_fog_colour_top[2])
	
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
	
	# Add rotation paramater if any rotation has been done and this is a box
	if (sh_type == "OBS" or sh_type == "DEC"):
		if (obj.rotation_euler[1] != 0.0 or obj.rotation_euler[2] != 0.0 or obj.rotation_euler[0] != 0.0):
			properties["rot"] = str(obj.rotation_euler[1]) + " " + str(obj.rotation_euler[2]) + " " + str(obj.rotation_euler[0])
	
	# Add template for all types of objects
	if (obj.sh_properties.sh_template):
		properties["template"] = obj.sh_properties.sh_template
	
	# Add mode appearance tag
	if (sh_type == "OBS"):
		mask = 0b0
		
		for v in [("training", 1), ("classic", 2), ("expert", 4), ("zen", 8), ("versus", 16), ("coop", 32)]:
			if (v[0] in obj.sh_properties.sh_mode):
				mask |= v[1]
		
		if (mask != 0b111111):
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
	if (sh_type == "BOX" and obj.sh_properties.sh_visible and not obj.sh_properties.sh_template):
		
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
		
		properties["tileSize"] = str(obj.sh_properties.sh_tilesize[0]) + " " + str(obj.sh_properties.sh_tilesize[1]) + " " + str(obj.sh_properties.sh_tilesize[2])
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
	file_header = "<!-- Exporter: Smash Hit Tools v" + str(bl_info["version"][0]) + "." + str(bl_info["version"][1]) + "." + str(bl_info["version"][2]) + " -->\n"
	
	# Get final string
	content = file_header + et.tostring(level_root, encoding = "unicode")
	
	return content

def sh_export_segment(filepath, context, *, compress = False, params = {"sh_vrmultiply": 1.0, "sh_box_bake_mode": "Mesh"}):
	"""
	This function exports the blender scene to a Smash Hit compatible XML file.
	"""
	
	context.window.cursor_set('WAIT')
	
	content = createSegmentText(context, params)
	
	##
	## Handle test server mode
	##
	
	# TODO: Split into function exportSegmentTest
	if (params.get("sh_test_server", False) == True):
		# Make dirs
		tempdir = tempfile.gettempdir() + "/shbt-testserver"
		os.makedirs(tempdir, exist_ok = True)
		
		# Delete old mesh file
		if (ospath.exists(tempdir + "/segment.mesh")):
			os.remove(tempdir + "/segment.mesh")
		
		# Write mesh if needed
		if (params.get("sh_box_bake_mode", "Mesh") == "Mesh"):
			bake_mesh.BAKE_UNSEEN_FACES = params.get("bake_menu_segment", False)
			bake_mesh.ABMIENT_OCCLUSION_ENABLED = params.get("bake_vertex_light", True)
			bake_mesh.LIGHTING_ENABLED = params.get("lighting_enabled", False)
			bake_mesh.bakeMeshToFile(content, tempdir + "/segment.mesh", params.get("sh_meshbake_template", None))
		
		# Write XML
		with open(tempdir + "/segment.xml", "w") as f:
			f.write(content)
		
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
		bake_mesh.bakeMeshToFile(content, meshfile, (params["sh_meshbake_template"] if params["sh_meshbake_template"] else None))
	
	# Write out file
	if (not compress):
		with open(filepath, "w") as f:
			f.write(content)
	else:
		with gzip.open(filepath, "wb") as f:
			f.write(content.encode())
	
	context.window.cursor_set('DEFAULT')
	
	return {"FINISHED"}

## UI-related classes

class ExportHelper2:
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

def tryTemplatesPath():
	"""
	Try to get the path of the templates.xml file automatically
	"""
	
	try:
		print("Smash Hit Tools: Auto find templates invoked.")
		print("Smash Hit Tools: Trying to find templates from APK Editor Studio")
		
		##
		## Templates from APK Editor Studio
		##
		
		# Get the search path
		search_path = tempfile.gettempdir() + "/apk-editor-studio/apk"
		
		print(f"Smash Hit Tools: Try to search in: \"{search_path}\"")
		
		# Enumerate files
		dirs = os.listdir(search_path)
		
		# Search for templates.xml and set path
		path = ""
		
		for d in dirs:
			cand = search_path + "/" + d + "/assets/templates.xml.mp3"
			
			print(f"Smash Hit Tools: Try file: \"{cand}\"")
			
			if ospath.exists(cand):
				path = cand
				break
		
		##
		## Templates file from home directory
		##
		
		homedir_templates = str(pathlib.Path.home()) + "/smash-hit-templates.xml"
		
		if (not path and ospath.exists(homedir_templates)):
			path = homedir_templates
		
		print(f"Smash Hit Tools: Got file: \"{path}\"")
		
		return path
	except FileNotFoundError:
		return ""

class sh_ExportCommon(bpy.types.Operator, ExportHelper2):
	"""
	Common code and values between export types
	"""
	
	def __init__(self):
		"""
		Automatic templates.xml detection
		"""
		
		if (not self.sh_meshbake_template):
			self.sh_meshbake_template = tryTemplatesPath()
	
	sh_meshbake_template: StringProperty(
		name = "Template",
		description = "A relitive or full path to the template file used for baking meshes. If you use APK Editor Studio and the Smash Hit APK is open, the path to the file will be pre-filled",
		default = "",
		subtype = "FILE_PATH",
		maxlen = SH_MAX_STR_LEN,
		)

class sh_export(sh_ExportCommon):
	"""
	Uncompressed segment export
	"""
	bl_idname = "sh.export"
	bl_label = "Export Segment"
	
	filename_ext = ".xml.mp3"
	filter_glob = bpy.props.StringProperty(default='*.xml.mp3', options={'HIDDEN'}, maxlen=255)
	
	def execute(self, context):
		sh_properties = context.scene.sh_properties
		
		result = sh_export_segment(
			self.filepath,
			context,
			params = {
				"sh_meshbake_template": self.sh_meshbake_template,
				"sh_vrmultiply": sh_properties.sh_vrmultiply,
				"sh_box_bake_mode": sh_properties.sh_box_bake_mode,
				"bake_menu_segment": sh_properties.sh_menu_segment,
				"bake_vertex_light": sh_properties.sh_ambient_occlusion,
				"lighting_enabled": sh_properties.sh_lighting,
			}
		)
		
		return result

def sh_draw_export(self, context):
	self.layout.operator("sh.export", text="Segment (.xml.mp3)")

class sh_export_gz(sh_ExportCommon):
	"""
	Compressed segment export
	"""
	
	bl_idname = "sh.export_compressed"
	bl_label = "Export Compressed Segment"
	
	filename_ext = ".xml.gz.mp3"
	filter_glob = bpy.props.StringProperty(default='*.xml.gz.mp3', options={'HIDDEN'}, maxlen=255)
	
	def execute(self, context):
		sh_properties = context.scene.sh_properties
		
		result = sh_export_segment(
			self.filepath,
			context,
			compress = True,
			params = {
				"sh_vrmultiply": sh_properties.sh_vrmultiply,
				"sh_box_bake_mode": sh_properties.sh_box_bake_mode,
				"sh_meshbake_template": self.sh_meshbake_template,
				"bake_menu_segment": sh_properties.sh_menu_segment,
				"bake_vertex_light": sh_properties.sh_ambient_occlusion,
				"lighting_enabled": sh_properties.sh_lighting,
			}
		)
		
		return result

def sh_draw_export_gz(self, context):
	self.layout.operator("sh.export_compressed", text="Compressed Segment (.xml.gz.mp3)")

class sh_export_test(Operator):
	"""
	Compressed segment export
	"""
	
	bl_idname = "sh.export_test_server"
	bl_label = "Export Segment to Test Server"
	
	def execute(self, context):
		sh_properties = context.scene.sh_properties
		
		result = sh_export_segment(
			None,
			context,
			params = {
				"sh_vrmultiply": sh_properties.sh_vrmultiply,
				"sh_box_bake_mode": sh_properties.sh_box_bake_mode,
				"bake_menu_segment": sh_properties.sh_menu_segment,
				"bake_vertex_light": sh_properties.sh_ambient_occlusion,
				"lighting_enabled": sh_properties.sh_lighting,
				"sh_test_server": True,
				"sh_meshbake_template": tryTemplatesPath()
			}
		)
		
		return result

def sh_draw_export_test(self, context):
	self.layout.operator("sh.export_test_server", text="Smash Hit Quick Test Server")

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

# UI-related

# Uncompressed
class sh_import(bpy.types.Operator, ExportHelper2):
	bl_idname = "sh.import"
	bl_label = "Import Segment"
	
	check_extension = False
	filename_ext = ".xml.mp3"
	filter_glob = bpy.props.StringProperty(default='*.xml.mp3', options={'HIDDEN'}, maxlen=255)
	
	def execute(self, context):
		return sh_import_segment(self.filepath, context)

def sh_draw_import(self, context):
	self.layout.operator("sh.import", text="Segment (.xml.mp3)")

# Compressed
class sh_import_gz(bpy.types.Operator, ExportHelper2):
	bl_idname = "sh.import_gz"
	bl_label = "Import Compressed Segment"
	
	check_extension = False
	filename_ext = ".xml.gz.mp3"
	filter_glob = bpy.props.StringProperty(default='*.xml.gz.mp3', options={'HIDDEN'}, maxlen=255)
	
	def execute(self, context):
		return sh_import_segment(self.filepath, context, True)

def sh_draw_import_gz(self, context):
	self.layout.operator("sh.import_gz", text="Compressed Segment (.xml.gz.mp3)")

## EDITOR
## The following things are more related to the editor and are not specifically
## for exporting or importing segments.

class sh_SceneProperties(PropertyGroup):
	"""
	Segment (scene) properties
	"""
	
	sh_len: FloatVectorProperty(
		name = "Size",
		description = "Segment size (Width, Height, Depth). Hint: Last paramater changes the length (depth) of the segment",
		subtype = "XYZ",
		default = (12.0, 10.0, 8.0), 
		min = 0.0,
		max = 1024.0,
	) 
	
	sh_box_bake_mode: EnumProperty(
		name = "Box bake mode",
		description = "This will control how the boxes should be exported. Hover over each option for an explation of how it works",
		items = [ 
			('Mesh', "Mesh", "Exports a .mesh file alongside the segment for showing visible box geometry"),
			('StoneHack', "Stone hack", "Adds a custom obstacle named 'stone' for every box that attempts to simulate stone. Only colour is supported: there are no textures"),
			('None', "None", "Don't do anything related to baking stone; only exports the raw segment data"),
		],
		default = "Mesh"
		)
	
	sh_template: StringProperty(
		name = "Template",
		description = "The template paramater that is passed for the entire segment",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_softshadow: FloatProperty(
		name = "Soft shadow",
		description = "Opacity of soft shadow on dynamic objects",
		default = -0.001,
		min = -0.001,
		max = 1.0
		)
	
	sh_vrmultiply: FloatProperty(
		name = "Segment strech",
		description = "This option tries to strech the segment's depth to make more time between obstacles. The intent is to allow it to be played in Smash Hit VR easier and without modifications to the segment",
		default = 1.0,
		min = 0.75,
		max = 4.0,
		)
	
	sh_light_left: FloatProperty(
		name = "Left",
		description = "Light going on to the left side of boxes",
		default = 1.0,
		min = 0.0,
		max = 1.0,
		)
	
	sh_light_right: FloatProperty(
		name = "Right",
		description = "Light going on to the right side of boxes",
		default = 1.0,
		min = 0.0,
		max = 1.0,
		)
	
	sh_light_top: FloatProperty(
		name = "Top",
		description = "Light going on to the top side of boxes",
		default = 1.0,
		min = 0.0,
		max = 1.0,
		)
	
	sh_light_bottom: FloatProperty(
		name = "Bottom",
		description = "Light going on to the bottom side of boxes",
		default = 1.0,
		min = 0.0,
		max = 1.0,
		)
	
	sh_light_front: FloatProperty(
		name = "Front",
		description = "Light going on to the front side of boxes",
		default = 1.0,
		min = 0.0,
		max = 1.0,
		)
	
	sh_light_back: FloatProperty(
		name = "Back",
		description = "Light going on to the back side of boxes",
		default = 1.0,
		min = 0.0,
		max = 1.0,
		)
	
	sh_menu_segment: BoolProperty(
		name = "Menu segment mode",
		description = "Treats the segment like it will appear on the main menu. Bakes faces that cannot be seen by the player",
		default = False
		)
	
	sh_ambient_occlusion: BoolProperty(
		name = "Ambient occlusion",
		description = "Enables ambient occlusion (per-vertex lighting)",
		default = True
		)
	
	sh_lighting: BoolProperty(
		name = "Lighting",
		description = "Enables some lighting features when baking the mesh",
		default = False
		)
	
	sh_lighting_ambient: FloatVectorProperty(
		name = "Ambient",
		description = "Colour and intensity of the ambient light",
		subtype = "COLOR_GAMMA",
		default = (0.0, 0.0, 0.0), 
		min = 0.0,
		max = 1.0,
	)
	
	sh_fog_colour_top: FloatVectorProperty(
		name = "Top fog",
		description = "Fog colour for Blender Tools quick test. While this does use the fogcolor xml attribute, this property cannot be inherited from templates or used like a normal property",
		subtype = "COLOR_GAMMA",
		default = (1.0, 1.0, 1.0), 
		min = 0.0,
		max = 1.0,
	)
	
	sh_fog_colour_bottom: FloatVectorProperty(
		name = "Bottom fog",
		description = "Fog colour for Blender Tools quick test. While this does use the fogcolor xml attribute, this property cannot be inherited from templates or used like a normal property",
		subtype = "COLOR_GAMMA",
		default = (0.0, 0.0, 0.0), 
		min = 0.0,
		max = 1.0,
	)

# Object (box/obstacle/powerup/decal/water) properties

class sh_EntityProperties(PropertyGroup):
	
	sh_type: EnumProperty(
		name = "Kind",
		description = "The kind of object that the currently selected object should be treated as.",
		items = [ ('BOX', "Box", ""),
				  ('OBS', "Obstacle", ""),
				  ('DEC', "Decal", ""),
				  ('POW', "Power-up", ""),
				  ('WAT', "Water", ""),
				],
		default = "BOX"
		)
	
	sh_template: StringProperty(
		name = "Template",
		description = "The template for the obstacle/box (see templates.xml), remember that this can be easily overridden per obstacle/box",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_use_chooser: BoolProperty(
		name = "Use obstacle chooser",
		description = "Use the obstacle chooser instead of typing the name by hand",
		default = False,
		)
	
	sh_obstacle: StringProperty(
		name = "Obstacle",
		description = "Type of obstacle to be used (as a file name string)",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_obstacle_chooser: EnumProperty(
		name = "Obstacle",
		description = "Type of obstacle to be used (pick a name)",
		items = obstacle_db.OBSTACLES,
		default = "scoretop",
		)
	
	sh_powerup: EnumProperty(
		name = "Power-up",
		description = "The type of power-up that will appear",
		items = [
			('ballfrenzy', "Ball Frenzy", "Allows the player infinite balls for some time"),
			('slowmotion', "Slow Motion", "Slows down the game"),
			('nitroballs', "Nitro Balls", "Turns balls into exposlives for a short period of time"),
			None,
			('barrel', "Barrel", "Creates a large explosion which breaks glass (lefover from beta versions)"),
			('multiball', "Multi-ball", "Does not work anymore. Old power up that would enable five-ball multiball"),
			('freebie', "Freebie", "Does not work anymore. Old power up found in binary strings but no known usage"),
			('antigravity', "Anti-gravity", "Does not work anymore. Old power up that probably would have reversed gravity"),
			('rewind', "Rewind", "Does not work anymore. Old power up that probably would have reversed time"),
			('sheild', "Sheild", "Does not work anymore. Old power up that probably would have protected the player"),
			('homing', "Homing", "Does not work anymore. Old power up that probably would have homed to obstacles"),
			('life', "Life", "Does not work anymore. Old power up that gave the player a life"),
			('balls', "Balls", "Does not work anymore. Old power up that gave the player ten balls"),
		],
		default = "ballfrenzy",
		)
	
	sh_export: BoolProperty(
		name = "Export object",
		description = "If the object should be exported to the XML at all. Change \"hidden\" if you'd like it to be hidden but still present in the exported file",
		default = True,
		)
	
	sh_hidden: BoolProperty(
		name = "Hidden",
		description = "If the obstacle will show in the level",
		default = False,
		)
	
	sh_mode: EnumProperty(
		name = "Mode",
		options = {"ENUM_FLAG"},
		description = "The game modes in which this obstacle should appear",
		items = [
			('training', "Training", "The easiest game mode which removes randomisation", 1),
			('classic', "Classic", "The primary game mode in Smash Hit", 2),
			('expert', "Mayhem", "The harder version of classic mode, with boss fights", 4),
			('zen', "Zen", "A relaxing sandbox mode which removes hit detection", 8),
			('versus', "Versus", "Two player versus mode where each player has their own ball count", 16),
			('coop', "Co-op", "Two player co-op mode where both players share a ball count", 32),
		],
		default = {'training', 'classic', 'expert', 'zen', 'versus', 'coop'},
		)
	
	##################
	# Mesh properties
	##################
	
	sh_visible: BoolProperty(
		name = "Visible",
		description = "If the box will appear in the exported mesh",
		default = False
		)
	
	sh_use_multitile: BoolProperty(
		name = "Tile per-side",
		description = "Specifiy a colour for each parallel pair of faces on the box",
		default = False,
		)
	
	sh_tile: IntProperty(
		name = "Tile",
		description = "The texture that will appear on the surface of the box or decal",
		default = 0,
		min = 0,
		max = 63
		)
	
	sh_tile1: IntProperty(
		name = "Right Left",
		description = "The texture that will appear on the surface of the box or decal",
		default = 0,
		min = 0,
		max = 63
		)
	
	sh_tile2: IntProperty(
		name = "Top Bottom",
		description = "The texture that will appear on the surface of the box or decal",
		default = 0,
		min = 0,
		max = 63
		)
	
	sh_tile3: IntProperty(
		name = "Front Back",
		description = "The texture that will appear on the surface of the box or decal",
		default = 0,
		min = 0,
		max = 63
		)
	
	sh_tilerot: IntVectorProperty(
		name = "Tile orientation",
		description = "Orientation of the tile, where 0 is facing up",
		default = (0, 0, 0), 
		min = 0,
		max = 3,
	) 
	
	sh_tilesize: FloatVectorProperty(
		name = "Tile size",
		description = "The appearing size of the tiles on the box when exported. In RightLeft, TopBottom, FrontBack",
		default = (1.0, 1.0, 1.0), 
		min = 0.0,
		max = 128.0,
		size = 3
	) 
	
	########################
	# Back to normal things
	########################
	
	sh_decal: IntProperty(
		name = "Decal",
		description = "The image ID for the decal (negitive numbers are doors)",
		default = 1,
		min = -4,
		max = 63
		)
	
	sh_reflective: BoolProperty(
		name = "Reflective",
		description = "If this box should show reflections",
		default = False
		)
	
	#############
	# Paramaters
	#############
	
	sh_param0: StringProperty(
		name = "param0",
		description = "Parameter which is given to the obstacle when spawned",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_param1: StringProperty(
		name = "param1",
		description = "Parameter which is given to the obstacle when spawned",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_param2: StringProperty(
		name = "param2",
		description = "Parameter which is given to the obstacle when spawned",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_param3: StringProperty(
		name = "param3",
		description = "Parameter which is given to the obstacle when spawned",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_param4: StringProperty(
		name = "param4",
		description = "Parameter which is given to the obstacle when spawned",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_param5: StringProperty(
		name = "param5",
		description = "Parameter which is given to the obstacle when spawned",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_param6: StringProperty(
		name = "param6",
		description = "Parameter which is given to the obstacle when spawned",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_param7: StringProperty(
		name = "param7",
		description = "Parameter which is given to the obstacle when spawned",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_param8: StringProperty(
		name = "param8",
		description = "Parameter which is given to the obstacle when spawned",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_param9: StringProperty(
		name = "param9",
		description = "Parameter which is given to the obstacle when spawned",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_param10: StringProperty(
		name = "param10",
		description = "Parameter which is given to the obstacle when spawned",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_param11: StringProperty(
		name = "param11",
		description = "Parameter which is given to the obstacle when spawned",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	###############
	# Other values
	###############
	
	sh_havetint: BoolProperty(
		name = "Add decal colourisation",
		description = "Changes the tint (colourisation) of the decal",
		default = False
		)
	
	sh_use_multitint: BoolProperty(
		name = "Colour per-side",
		description = "Specifiy a colour for each parallel pair of faces on the box",
		default = False,
		)
	
	sh_tint: FloatVectorProperty(
		name = "Colour",
		description = "The colour to be used for tinting, colouring and mesh data",
		subtype = "COLOR_GAMMA",
		default = (0.5, 0.5, 0.5, 1.0), 
		size = 4,
		min = 0.0,
		max = 1.0
	)
	
	sh_tint1: FloatVectorProperty(
		name = "Right Left",
		description = "The colour to be used for tinting, colouring and mesh data",
		subtype = "COLOR_GAMMA",
		default = (0.5, 0.5, 0.5, 1.0), 
		size = 4,
		min = 0.0,
		max = 1.0
	)
	
	sh_tint2: FloatVectorProperty(
		name = "Top Bottom",
		description = "The colour to be used for tinting, colouring and mesh data",
		subtype = "COLOR_GAMMA",
		default = (0.5, 0.5, 0.5, 1.0), 
		size = 4,
		min = 0.0,
		max = 1.0
	)
	
	sh_tint3: FloatVectorProperty(
		name = "Front Back",
		description = "The colour to be used for tinting, colouring and mesh data",
		subtype = "COLOR_GAMMA",
		default = (0.5, 0.5, 0.5, 1.0), 
		size = 4,
		min = 0.0,
		max = 1.0
	)
	
	sh_blend: FloatProperty(
		name = "Blend mode",
		description = "How the colour of the decal and the existing colour will be blended. 1 = normal, 0 = added or numbers in between",
		default = 1.0,
		min = 0.0,
		max = 1.0,
	)
	
	sh_size: FloatVectorProperty(
		name = "Size",
		description = "The size of the object when exported. For boxes this is the tileSize property",
		default = (1.0, 1.0), 
		min = 0.0,
		max = 256.0,
		size = 2,
	)
	
	sh_glow: FloatProperty(
		name = "Glow",
		description = "The intensity of the light in \"watts\"; zero if this isn't a light",
		default = 0.0,
		min = 0.0,
		max = 1000.0,
	)

class sh_SegmentPanel(Panel):
	bl_label = "Smash Hit"
	bl_idname = "OBJECT_PT_segment_panel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Scene"
	
	@classmethod
	def poll(self, context):
		return True
	
	def draw(self, context):
		layout = self.layout
		scene = context.scene
		sh_properties = scene.sh_properties
		
		layout.prop(sh_properties, "sh_len")
		layout.prop(sh_properties, "sh_box_bake_mode")
		layout.prop(sh_properties, "sh_template")
		layout.prop(sh_properties, "sh_softshadow")
		layout.prop(sh_properties, "sh_vrmultiply")
		
		sub = layout.box()
		sub.label(text = "Light", icon = "LIGHT")
		sub.label(text = "Basic lighting")
		sub.prop(sh_properties, "sh_light_right")
		sub.prop(sh_properties, "sh_light_left")
		sub.prop(sh_properties, "sh_light_top")
		sub.prop(sh_properties, "sh_light_bottom")
		sub.prop(sh_properties, "sh_light_front")
		sub.prop(sh_properties, "sh_light_back")
		
		sub.label(text = "Advanced lighting")
		sub.prop(sh_properties, "sh_lighting")
		if (sh_properties.sh_lighting):
			sub.prop(sh_properties, "sh_lighting_ambient")
		
		layout.prop(sh_properties, "sh_fog_colour_top")
		layout.prop(sh_properties, "sh_fog_colour_bottom")
		
		layout.prop(sh_properties, "sh_menu_segment")
		layout.prop(sh_properties, "sh_ambient_occlusion")
		
		layout.separator()

class sh_ObstaclePanel(Panel):
	bl_label = "Smash Hit"
	bl_idname = "OBJECT_PT_obstacle_panel"
	bl_space_type = "VIEW_3D"   
	bl_region_type = "UI"
	bl_category = "Item"
	bl_context = "objectmode"
	
	@classmethod
	def poll(self, context):
		return context.object is not None
	
	def draw(self, context):
		layout = self.layout
		object = context.object
		sh_properties = object.sh_properties
		
		# All objects will have all properties, but only some will be used for
		# each of obstacle there is.
		layout.prop(sh_properties, "sh_type")
		
		# Obstacle type for obstacles
		if (sh_properties.sh_type == "OBS"):
			layout.prop(sh_properties, "sh_use_chooser", toggle = 1)
			if (sh_properties.sh_use_chooser):
				layout.prop(sh_properties, "sh_obstacle_chooser")
			else:
				layout.prop(sh_properties, "sh_obstacle")
		
		# Decal number for decals
		if (sh_properties.sh_type == "DEC"):
			layout.prop(sh_properties, "sh_decal")
		
		# Template for boxes and obstacles
		if (sh_properties.sh_type == "OBS" or (sh_properties.sh_type == "BOX" and not sh_properties.sh_visible)):
			layout.prop(sh_properties, "sh_template")
		
		# Refelective and tile property for boxes
		if (sh_properties.sh_type == "BOX"):
			layout.prop(sh_properties, "sh_reflective")
			layout.prop(sh_properties, "sh_visible")
			
			if (sh_properties.sh_visible):
				sub = layout.box()
				
				sub.label(text = "Colour", icon = "COLOR")
				if (not sh_properties.sh_use_multitint):
					sub.prop(sh_properties, "sh_use_multitint", text = "Uniform", toggle = 1)
					sub.prop(sh_properties, "sh_tint")
				else:
					sub.prop(sh_properties, "sh_use_multitint", text = "Per-axis", toggle = 1)
					sub.prop(sh_properties, "sh_tint1")
					sub.prop(sh_properties, "sh_tint2")
					sub.prop(sh_properties, "sh_tint3")
				
				sub = layout.box()
				
				sub.label(text = "Tile", icon = "TEXTURE")
				if (not sh_properties.sh_use_multitile):
					sub.prop(sh_properties, "sh_use_multitile", text = "Uniform", toggle = 1)
					sub.prop(sh_properties, "sh_tile")
				else:
					sub.prop(sh_properties, "sh_use_multitile", text = "Per-axis", toggle = 1)
					sub.prop(sh_properties, "sh_tile1")
					sub.prop(sh_properties, "sh_tile2")
					sub.prop(sh_properties, "sh_tile3")
				
				if (context.scene.sh_properties.sh_lighting):
					sub = layout.box()
					
					sub.label(text = "Light", icon = "LIGHT")
					sub.prop(sh_properties, "sh_glow")
				
				sub = layout.box()
				
				sub.label(text = "Transforms", icon = "GRAPH")
				sub.prop(sh_properties, "sh_tilesize")
				sub.prop(sh_properties, "sh_tilerot")
		
		# Colourisation and blend for decals
		if (sh_properties.sh_type == "DEC"):
			layout.prop(sh_properties, "sh_havetint")
			if (sh_properties.sh_havetint):
				layout.prop(sh_properties, "sh_tint")
				layout.prop(sh_properties, "sh_tintalpha")
			layout.prop(sh_properties, "sh_blend")
		
		# Mode for obstacles
		if (sh_properties.sh_type == "OBS"):
			layout.prop(sh_properties, "sh_mode")
		
		# Power-up name for power-ups
		if (sh_properties.sh_type == "POW"):
			layout.prop(sh_properties, "sh_powerup")
		
		# Size for decals
		if (sh_properties.sh_type == "DEC"):
			layout.prop(sh_properties, "sh_size")
		
		# Hidden property
		if (sh_properties.sh_type != "BOX"):
			layout.prop(sh_properties, "sh_hidden")
		
		# Paramaters for boxes
		if (sh_properties.sh_type == "OBS"):
			sub = layout.box()
			
			sub.label(text = "Parameters", icon = "SETTINGS")
			sub.prop(sh_properties, "sh_param0", text = "")
			sub.prop(sh_properties, "sh_param1", text = "")
			sub.prop(sh_properties, "sh_param2", text = "")
			sub.prop(sh_properties, "sh_param3", text = "")
			sub.prop(sh_properties, "sh_param4", text = "")
			sub.prop(sh_properties, "sh_param5", text = "")
			sub.prop(sh_properties, "sh_param6", text = "")
			sub.prop(sh_properties, "sh_param7", text = "")
			sub.prop(sh_properties, "sh_param8", text = "")
			sub.prop(sh_properties, "sh_param9", text = "")
			sub.prop(sh_properties, "sh_param10", text = "")
			sub.prop(sh_properties, "sh_param11", text = "")
		
		# Option to export object or not
		layout.prop(sh_properties, "sh_export")
		
		layout.separator()

classes = (
	# Ignore the naming scheme for classes, please
	sh_SceneProperties,
	sh_EntityProperties,
	sh_SegmentPanel,
	sh_ObstaclePanel,
	sh_export,
	sh_export_gz,
	sh_export_test,
	sh_import,
	sh_import_gz,
)

def register():
	from bpy.utils import register_class
	
	for cls in classes:
		register_class(cls)
	
	bpy.types.Scene.sh_properties = PointerProperty(type=sh_SceneProperties)
	bpy.types.Object.sh_properties = PointerProperty(type=sh_EntityProperties)
	
	# Add the export operator to menu
	bpy.types.TOPBAR_MT_file_export.append(sh_draw_export)
	bpy.types.TOPBAR_MT_file_export.append(sh_draw_export_gz)
	bpy.types.TOPBAR_MT_file_export.append(sh_draw_export_test)
	
	# Add import operators to menu
	bpy.types.TOPBAR_MT_file_import.append(sh_draw_import)
	bpy.types.TOPBAR_MT_file_import.append(sh_draw_import_gz)
	
	# Start server
	global g_process_test_server
	
	if (g_process_test_server):
		g_process_test_server = server.runServerProcess()

def unregister():
	from bpy.utils import unregister_class
	
	for cls in reversed(classes):
		unregister_class(cls)
	
	del bpy.types.Scene.sh_properties
	
	# Shutdown server
	global g_process_test_server
	
	if (g_process_test_server):
		g_process_test_server.terminate()
