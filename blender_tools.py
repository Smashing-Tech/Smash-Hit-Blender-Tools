"""
Smash Hit segment export tool for Blender
"""

# The path to a copy of MeshBake or compatible script (*.py, 0.3.0 or later)
# TODO: Consider removing this again?
DEV_MESHBAKE_ENV_PATH = "You need to set me!!"
SH_MAX_STR_LEN = 512

bl_info = {
	"name": "Smash Hit Segment Tools",
	"description": "Segment exporter and item property editor for Smash Hit",
	"author": "Knot126",
	"version": (1, 2, 5),
	"blender": (2, 83, 0),
	"location": "File > Import/Export and 3D View > Tools",
	"warning": "",
	"wiki_url": "https://smashingmods.fandom.com/wiki/Knot126/Smash_Hit_Blender_Tools",
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
import importlib.util as imut

from bpy.props import (StringProperty, BoolProperty, IntProperty, FloatProperty, FloatVectorProperty, EnumProperty, PointerProperty)
from bpy.types import (Panel, Menu, Operator, PropertyGroup)

## Segment Export
## All of the following is related to exporting segments.

def sh_create_root(scene, params):
	"""
	Creates the main root and returns it
	"""
	
	size = {"X": scene.sh_len[0], "Y": scene.sh_len[1], "Z": scene.sh_len[2]}
	
	# VR Multiply setting
	if (params["sh_vrmultiply"] > 1.05):
		size["Z"] = size["Z"] * params["sh_vrmultiply"]
	
	# Initial segment properties, like size
	seg_props = {
	   "size": str(size["X"]) + " " + str(size["Y"]) + " " + str(size["Z"])
	}
	
	# Lighting from KBT
	if (scene.sh_light[0] != 1.0): seg_props["lightLeft"] = str(scene.sh_light[0])
	if (scene.sh_light[1] != 1.0): seg_props["lightRight"] = str(scene.sh_light[1])
	if (scene.sh_light[2] != 1.0): seg_props["lightTop"] = str(scene.sh_light[2])
	if (scene.sh_light[3] != 1.0): seg_props["lightBottom"] = str(scene.sh_light[3])
	if (scene.sh_light[4] != 1.0): seg_props["lightFront"] = str(scene.sh_light[4])
	if (scene.sh_light[5] != 1.0): seg_props["lightBack"] = str(scene.sh_light[5])
	
	if (scene.sh_lightfactor != 0.666):
		seg_props["meshbake_lightFactor"] = str(scene.sh_lightfactor)
	
	if (params["disable_lighting"]):
		seg_props["meshbake_disableLight"] = "1"
	
	# Check for the template attrib and set
	if (scene.sh_template):
		seg_props["template"] = scene.sh_template
	
	# Check for softshadow attrib and set
	if (scene.sh_softshadow >= 0.0):
		seg_props["softshadow"] = str(scene.sh_softshadow)
	
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
	if (params["sh_vrmultiply"] > 1.05):
		position["Z"] = position["Z"] * params["sh_vrmultiply"]
	
	# The only gaurrented to exsist is pos
	properties = {
		"pos": str(position["X"]) + " " + str(position["Y"]) + " " + str(position["Z"]),
	}
	
	# Type for obstacles
	if (obj.sh_properties.sh_type == "OBS"):
		properties["type"] = obj.sh_properties.sh_obstacle
	
	# Type for power-ups
	if (obj.sh_properties.sh_type == "POW"):
		properties["type"] = obj.sh_properties.sh_powerup
		
	# Hidden for all types
	if (obj.sh_properties.sh_hidden):
		properties["hidden"] = "1"
	else:
		properties["hidden"] = "0"
	
	# Add size for boxes
	if (obj.sh_properties.sh_type == "BOX"):
		# Again, swapped becuase of Smash Hit's demensions
		size = {"X": obj.dimensions[1] / 2, "Y": obj.dimensions[2] / 2, "Z": obj.dimensions[0] / 2}
		
		# VR Multiply setting
		if (params["sh_vrmultiply"] > 1.05 and (abs(size["Z"]) > 2.0)):
			size["Z"] = size["Z"] * params["sh_vrmultiply"]
		
		properties["size"] = str(size["X"]) + " " + str(size["Y"]) + " " + str(size["Z"])
	
	# Add rotation paramater if any rotation has been done and this is a box
	if (obj.sh_properties.sh_type == "OBS" or obj.sh_properties.sh_type == "DEC"):
		if (obj.rotation_euler[1] > 0.0 or obj.rotation_euler[2] > 0.0 or obj.rotation_euler[0] > 0.0):
			properties["rot"] = str(obj.rotation_euler[1]) + " " + str(obj.rotation_euler[2]) + " " + str(obj.rotation_euler[0])
	
	# Add template for all types of objects
	if (obj.sh_properties.sh_template):
		properties["template"] = obj.sh_properties.sh_template
	
	# Add mode appearance tag
	if (obj.sh_properties.sh_type == "OBS" and obj.sh_properties.sh_mode and obj.sh_properties.sh_mode != "0"):
		properties["mode"] = obj.sh_properties.sh_mode
	
	# Add reflection property for boxes if not default
	if (obj.sh_properties.sh_type == "BOX" and obj.sh_properties.sh_reflective):
		properties["reflection"] = "1"
	
	# Add decal number if this is a decal
	if (obj.sh_properties.sh_type == "DEC"):
		properties["tile"] = str(obj.sh_properties.sh_decal)
	
	# Add decal size if this is a decal (based on sh_size)
	if (obj.sh_properties.sh_type == "DEC"):
		properties["size"] = str(obj.sh_properties.sh_size[0]) + " " + str(obj.sh_properties.sh_size[1])
	
	# Add water size if this is a water (based on physical plane properties)
	if (obj.sh_properties.sh_type == "WAT"):
		size = {"X": obj.dimensions[1] / 2, "Z": obj.dimensions[0] / 2}
		
		properties["size"] = str(size["X"]) + " " + str(size["Z"])
	
	# Set each of the tweleve paramaters if they are needed.
	if (obj.sh_properties.sh_type == "OBS"):
		for i in range(12):
			val = getattr(obj.sh_properties, "sh_param" + str(i))
			
			if (val):
				properties["param" + str(i)] = val
	
	# Set tint for decals
	if (obj.sh_properties.sh_havetint and obj.sh_properties.sh_type == "DEC"):
		properties["color"] = str(obj.sh_properties.sh_tint[0]) + " " + str(obj.sh_properties.sh_tint[1]) + " " + str(obj.sh_properties.sh_tint[2]) + " " + str(obj.sh_properties.sh_tint[3])
	
	if (obj.sh_properties.sh_type == "BOX"):
		if (obj.sh_properties.sh_visible):
			properties["visible"] = "1"
		else:
			properties["visible"] = "0"
	
	# Set tile info for boxes if visible and there is no template specified
	if (obj.sh_properties.sh_type == "BOX" and obj.sh_properties.sh_visible and not obj.sh_properties.sh_template):
		properties["color"] = str(obj.sh_properties.sh_tint[0]) + " " + str(obj.sh_properties.sh_tint[1]) + " " + str(obj.sh_properties.sh_tint[2]) + " " + str(obj.sh_properties.sh_tint[3])
		properties["tile"] = str(obj.sh_properties.sh_tile)
		properties["tileSize"] = str(obj.sh_properties.sh_tilesize[0]) + " " + str(obj.sh_properties.sh_tilesize[1])
		if (obj.sh_properties.sh_tilerot[1] > 0.0 or obj.sh_properties.sh_tilerot[2] > 0.0 or obj.sh_properties.sh_tilerot[0] > 0.0):
			properties["tileRot"] = str(obj.sh_properties.sh_tilerot[1]) + " " + str(obj.sh_properties.sh_tilerot[2]) + " " + str(obj.sh_properties.sh_tilerot[0])
	
	# Set the tag name
	element_type = "entity"
	
	if (obj.sh_properties.sh_type == "BOX"):
		element_type = "box"
	elif (obj.sh_properties.sh_type == "OBS"):
		element_type = "obstacle"
	elif (obj.sh_properties.sh_type == "DEC"):
		element_type = "decal"
	elif (obj.sh_properties.sh_type == "POW"):
		element_type = "powerup"
	elif (obj.sh_properties.sh_type == "WAT"):
		element_type = "water"
	
	# Add the element to the document
	el = et.SubElement(level_root, element_type, properties)
	el.tail = "\n\t"
	if (params["isLast"]): # Fixes the issues with the last line of the file
		el.tail = "\n"
	
	if (params["sh_exportmode"] == "StoneHack" and obj.sh_properties.sh_type == "BOX" and obj.sh_properties.sh_visible):
		"""
		Export a fake obstacle that will represent stone in the level.
		"""
		
		el.tail = "\n\t\t"
		
		size = {"X": obj.dimensions[1] / 2, "Y": obj.dimensions[2] / 2, "Z": obj.dimensions[0] / 2}
		position = {"X": obj.location[1], "Y": obj.location[2], "Z": obj.location[0]}
		
		# VR Multiply setting
		if (params["sh_vrmultiply"] > 1.05):
			position["Z"] = position["Z"] * params["sh_vrmultiply"]
		
		if (params["sh_vrmultiply"] > 1.05 and ((scene.sh_len[2] / 2) - 0.5) < abs(size["Z"])):
			size["Z"] = size["Z"] * params["sh_vrmultiply"]
		
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
			properties["param8"] = "color=" + str(obj.sh_properties.sh_tint[0]) + " " + str(obj.sh_properties.sh_tint[1]) + " " + str(obj.sh_properties.sh_tint[2])
		
		el_stone = et.SubElement(level_root, "obstacle", properties)
		el_stone.tail = "\n\t"
		if (params["isLast"]):
			el_stone.tail = "\n"

def sh_export_segment(fp, context, *, compress = False, params = {"sh_vrmultiply": 1.0, "sh_exportmode": "Mesh"}):
	"""
	This function exports the blender scene to a Smash Hit compatible XML file.
	"""
	
	context.window.cursor_set('WAIT')
	
	scene = context.scene.sh_properties
	b_scene = context.scene
	level_root = sh_create_root(scene, params)
	
	for i in range(len(bpy.data.objects)):
		obj = bpy.data.objects[i]
		
		if (not obj.sh_properties.sh_export):
			continue
		
		params["isLast"] = False
		if (i == (len(bpy.data.objects) - 1)):
			params["isLast"] = True
		
		sh_add_object(level_root, scene, obj, params)
	
	# Write the file
	
	file_header = "<!-- Exported with Smash Hit Blender Tools v" + str(bl_info["version"][0]) + "." + str(bl_info["version"][1]) + "." + str(bl_info["version"][2]) + " -->\n"
	if (params["sh_noheader"]):
		file_header = ""
	c = file_header + et.tostring(level_root, encoding = "unicode")
	
	# Cook the mesh if we need to
	meshfile = ospath.splitext(ospath.splitext(fp)[0])[0]
	if (compress):
		meshfile = ospath.splitext(meshfile)[0]
	meshfile += ".mesh.mp3"
	
	if (params["sh_exportmode"] == "Mesh"):
		sh_cookMesh042(et.fromstring(c), meshfile, params["sh_meshbake_template"])
	elif (params["sh_exportmode"] == "Custom"):
		print("Using the version of meshbake from:", DEV_MESHBAKE_ENV_PATH)
		
		# Load file as module
		spec = imut.spec_from_file_location("segtool.meshbake", DEV_MESHBAKE_ENV_PATH)
		CustomScript = imut.module_from_spec(spec)
		spec.loader.exec_module(CustomScript)
		
		# Call mesh cook function
		CustomScript.bt_cook_mesh(et.fromstring(c), meshfile)
	
	# Write out file
	if (not compress):
		with open(fp, "w") as f:
			f.write(c)
	else:
		with gzip.open(fp, "wb") as f:
			f.write(c.encode())
	
	context.window.cursor_set('DEFAULT')
	return {"FINISHED"}

def sh_load_templates(infile):
	"""
	Load templates from a file
	"""
	result = {}
	
	if (not infile):
		return result
	
	tree = et.parse(infile)
	root = tree.getroot()
	
	assert("templates" == root.tag)
	
	for child in root:
		assert("template" == child.tag)
		
		name = child.attrib["name"]
		attribs = child[0].attrib
		
		result[name] = attribs
	
	return result

## UI-related classes

class ExportHelper2:
	filepath: StringProperty(
		name="File Path",
		description="Filepath used for exporting the file",
		maxlen=1024,
		subtype='FILE_PATH',
	)
	check_existing: BoolProperty(
		name="Check Existing",
		description="Check and warn on overwriting existing files",
		default=True,
		options={'HIDDEN'},
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
		
		if self.check_extension is not None:
			if not self.filepath.endswith(self.filename_ext):
				self.filepath += self.filename_ext
				change_ext = True
		
		return change_ext

# Common values between export types
class sh_ExportCommon:
	sh_meshbake_template: StringProperty(
		name = "Template",
		description = "A relitive or full path to a template file. This is used for baking meshes",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_exportmode: EnumProperty(
		name = "Box Export Mode",
		description = "This will control how the boxes should be exported. Hover over each option for an explation of how it works",
		items = [ 
			('Mesh', "Mesh", "Exports a .mesh file alongside the segment for showing visible box geometry"),
			('StoneHack', "Stone hack", "Adds a custom obstacle named 'stone' for every box that attempts to simulate stone. Only colour is supported; there are no textures"),
			('Custom', "Custom script", "Uses a custom script for baking the mesh file (Note: need to set \'DEV_MESHBAKE_ENV_PATH\' in script file)"),
			('None', "None", "Don't do anything related to baking stone; only exports the raw segment data"),
		],
		default = "Mesh"
		)
	
	sh_vrmultiply: FloatProperty(
		name = "Segment strech",
		description = "This option tries to strech the segment's depth so it can be played in Smash Hit VR easier and without actual modification to the level. If you are serious about Smash Hit VR, avoid this setting, otherwise this can be a nice way to support VR without doing any extra work. Note that values less than 1.05 will use normal export",
		default = 1.0,
		min = 1.0,
		max = 2.5
		)
	
	nolighting: BoolProperty(
		name = "Disable lighting",
		description = "Disables vertex lighting in MeshBake",
		default = False
		)
	
	sh_disableheader: BoolProperty(
		name = "Disable header comment",
		description = "Disables the message that shows the segment was export with blender tools",
		default = False
		)

class sh_export(bpy.types.Operator, ExportHelper2, sh_ExportCommon):
	"""
	Uncompressed segment export
	"""
	bl_idname = "sh.export"
	bl_label = "Export Segment"
	
	filename_ext = ".xml.mp3"
	filter_glob = bpy.props.StringProperty(default='*.xml.mp3', options={'HIDDEN'}, maxlen=255)
	
	def execute(self, context):
		return sh_export_segment(
			self.filepath,
			context,
			params = {
				"sh_vrmultiply": self.sh_vrmultiply,
				"sh_exportmode": self.sh_exportmode,
				"disable_lighting": self.nolighting,
				"sh_meshbake_template": self.sh_meshbake_template,
				"sh_noheader": self.sh_disableheader,
			}
		)

def sh_draw_export(self, context):
	self.layout.operator("sh.export", text="Segment (.xml.mp3)")

class sh_export_gz(bpy.types.Operator, ExportHelper2, sh_ExportCommon):
	"""
	Compressed segment export
	"""
	
	bl_idname = "sh.export_compressed"
	bl_label = "Export Compressed Segment"
	
	filename_ext = ".xml.gz.mp3"
	filter_glob = bpy.props.StringProperty(default='*.xml.gz.mp3', options={'HIDDEN'}, maxlen=255)
	
	def execute(self, context):
		return sh_export_segment(
			self.filepath,
			context,
			compress = True, 
			params = {
				"sh_vrmultiply": self.sh_vrmultiply,
				"sh_exportmode": self.sh_exportmode,
				"disable_lighting": self.nolighting,
				"sh_meshbake_template": self.sh_meshbake_template,
				"sh_noheader": self.sh_disableheader,
			}
		)

def sh_draw_export_gz(self, context):
	self.layout.operator("sh.export_compressed", text="Compressed Segment (.xml.gz.mp3)")

## MESH BAKE
## This is just taken from meshbake

#MESHBAKE_START

PLANE_COORDS = (
	# (x, y, z, u, v),
	(-1.0, 1.0, 0.0, 0.0, 0.0), # top left
	(-1.0, -1.0, 0.0, 0.0, 0.125), # bottom left
	(1.0, -1.0, 0.0, 0.125, 0.125), # bottom right
	(1.0, 1.0, 0.0, 0.125, 0.0), # top right
)

PLANE_INDEX_BUFFER = (
	0, 1, 2, # first triangle
	0, 2, 3, # second triangle
)

def sh_cookMesh042(seg, outfile, templates_file = None):
	"""
	Builds a mesh file from an XML node
	
	Try to keep functions used only in this function within the scope of this
	function so its easier to embed.
	"""
	
	import struct
	import math
	import zlib
	
	# NOTE: Using bytearrays improves preformance.
	mesh_vert = bytearray()
	mesh_vert_count = 0
	mesh_index = bytearray()
	mesh = open(outfile, "wb")
	light_factor = 0.666
	
	def add_vert(x, y, z, u, v, r, g, b, a):
		"""
		Adds a vertex
		"""
		# print(f"{x}, {y}, {z}, {u}, {v}")
		
		nonlocal mesh_vert_count
		nonlocal mesh_vert
		nonlocal mesh_index
		mesh_vert_count += 1
		
		vert = b""
		index = b""
		
		# The position of this vertex
		vert += struct.pack("f", x)
		vert += struct.pack("f", y)
		vert += struct.pack("f", z)
		
		vert += struct.pack("f", u)
		vert += struct.pack("f", v)
		
		vert += struct.pack("B", max(0, min(r, 255)))
		vert += struct.pack("B", max(0, min(g, 255)))
		vert += struct.pack("B", max(0, min(b, 255)))
		vert += struct.pack("B", max(0, min(a, 255)))
		
		assert(len(vert) == 24)
		
		mesh_vert += vert
		
		return mesh_vert_count
	
	def add_cube(x, y, z, sx, sy, sz, t, tx, ty, c, lgt):
		"""
		Adds a cube
		"""
		nonlocal mesh_index
		nonlocal light_factor # the multiply of the light to make sure it's not too bright
		
		# Calculate position for the texture coordinates
		tile_u_offset = ((t % 8) + 1) / 8 - 0.125
		tile_v_offset = ((math.floor(((t + 1) / 8) - 0.125) + 1) / 8) - 0.125
		
		# Front and back faces
		for z_sign in [1.0, -1.0]:
			y_left = (sy * 2.0)
			y_offset = (sy * 1.0)
			
			while (y_left > 0.0):
				x_left = (sx * 2.0)
				x_offset = (sx * 1.0)
				
				y_cut = 1.0
				if (y_left < 1.0):
					y_cut = y_left
				
				while (x_left > 0.0):
					x_cut = 1.0
					if (x_left < 1.0):
						x_cut = x_left
					
					# Add indexes for one plane
					for i in range(len(PLANE_INDEX_BUFFER)):
						mesh_index += struct.pack("I", PLANE_INDEX_BUFFER[i] + mesh_vert_count)
					
					# Add verts for one plane
					for i in range(len(PLANE_COORDS)):
						add_vert(
							((PLANE_COORDS[i][0] * x_cut) * (tx * 0.5) + x + x_offset + ((1.0 - x_cut) * 0.5)) - 0.5,
							((PLANE_COORDS[i][1] * y_cut) * (ty * 0.5) + y + y_offset + ((1.0 - y_cut) * 0.5)) - 0.5,
							z + (sz * z_sign),
							(PLANE_COORDS[i][3] * x_cut) + tile_u_offset,
							(PLANE_COORDS[i][4] * y_cut) + tile_v_offset,
							int(c[0] * light_factor * (lgt[int((z_sign-1.0)/-2)])), 
							int(c[1] * light_factor * (lgt[int((z_sign-1.0)/-2)])), 
							int(c[2] * light_factor * (lgt[int((z_sign-1.0)/-2)])), 
							c[3])
					
					x_left -= tx
					x_offset -= tx
				# END while (x_left > 0.0)
				
				y_left -= ty
				y_offset -= ty
			# END while (y_left > 0.0)
		
		# Top and bottom faces
		# NOTE: This is only partially working...
		for j in [(0, 1), (1, 0)]:
			for y_sign in [1.0, -1.0]:
				z_left = (sz * 2.0)
				z_offset = (sz * 1.0)
				
				while (z_left > 0.0):
					x_left = (sx * 2.0)
					x_offset = (sx * 1.0)
					
					z_cut = 1.0
					if (z_left < 1.0):
						z_cut = z_left
					
					while (x_left > 0.0):
						x_cut = 1.0
						if (x_left < 1.0):
							x_cut = x_left
						
						# Add indexes for one plane
						for i in range(len(PLANE_INDEX_BUFFER)):
							mesh_index += struct.pack("I", PLANE_INDEX_BUFFER[i] + mesh_vert_count)
						
						# Add verts for one plane
						for i in range(len(PLANE_COORDS)):
							add_vert(
								(PLANE_COORDS[i][j[0]] * (tx * 0.5) + x + x_offset + ((1.0 - x_cut) * 0.5)) - 0.5,
								y + (sy * y_sign),
								(PLANE_COORDS[i][j[1]] * (ty * 0.5) + z + z_offset + ((1.0 - z_cut) * 0.5)) - 0.5,
								PLANE_COORDS[i][3] + tile_u_offset,
								PLANE_COORDS[i][4] + tile_v_offset,
								int(c[0] * light_factor * (lgt[2 + j[1]])), 
								int(c[1] * light_factor * (lgt[2 + j[1]])), 
								int(c[2] * light_factor * (lgt[2 + j[1]])), 
								c[3])
						
						x_left -= tx
						x_offset -= tx
					# END while (x_left > 0.0)
					
					z_left -= ty
					z_offset -= ty
				# END while (y_left > 0.0)
			# END for y_sign
		
		# Left and right side faces
		for j in [(0, 1), (1, 0)]:
			for x_sign in [1.0, -1.0]:
				y_left = (sy * 2.0)
				y_offset = (sy * 1.0)
				
				while (y_left > 0.0):
					y_cut = 1.0
					if (y_left < 1.0):
						y_cut = y_left
					
					z_left = (sz * 2.0)
					z_offset = (sz * 1.0)
					
					while (z_left > 0.0):
						z_cut = 1.0
						if (z_left < 1.0):
							z_cut = z_left
						
						# Add indexes for one plane
						for i in range(len(PLANE_INDEX_BUFFER)):
							mesh_index += struct.pack("I", PLANE_INDEX_BUFFER[i] + mesh_vert_count)
						
						# Add verts for one plane
						for i in range(len(PLANE_COORDS)):
							add_vert(
								x + (sx * x_sign),
								(PLANE_COORDS[i][j[0]] * (ty * 0.5) + y + y_offset + ((1.0 - y_cut) * 0.5)) - 0.5,
								(PLANE_COORDS[i][j[1]] * (tx * 0.5) + z + z_offset + ((1.0 - z_cut) * 0.5)) - 0.5,
								PLANE_COORDS[i][3] + tile_u_offset,
								PLANE_COORDS[i][4] + tile_v_offset,
								int(c[0] * light_factor * (lgt[4 + j[1]])), 
								int(c[1] * light_factor * (lgt[4 + j[1]])), 
								int(c[2] * light_factor * (lgt[4 + j[1]])), 
								c[3])
						
						z_left -= tx
						z_offset -= tx
					# END while (z_left > 0.0)
					
					y_left -= ty
					y_offset -= ty
				# END while (y_left > 0.0)
			# END for x_sign
	
	light_multiply = (
		float(seg.attrib.get("lightLeft", "1")), 
		float(seg.attrib.get("lightRight", "1")), 
		float(seg.attrib.get("lightTop", "1")), 
		float(seg.attrib.get("lightBottom", "1")), 
		float(seg.attrib.get("lightFront", "1")), 
		float(seg.attrib.get("lightBack", "1"))
	)
	
	if (seg.attrib.get("meshbake_disableLight", "0") == "1"):
		light_multiply = (2.0, 2.0, 2.0, 2.0, 2.0, 2.0)
	
	if ("meshbake_lightFactor" in seg.attrib):
		light_factor = float(seg.attrib["meshbake_lightFactor"])
	
	templates = sh_load_templates(templates_file)
	
	# Iterate through all the entities, and make boxes into meshes
	for entity in seg:
		if (entity.tag == "box"):
			properties = entity.attrib
			
			visible = properties.get("visible", "0")
			
			# NOTE: This behaiour seems more like what Smash Hit Editor does.
			# Previously, this would only export if visible == "1", but now it
			# does not require that stone be visible. New versions of Blender
			# Tools will now set visible property explicitly.
			if (visible == "0"):
				continue
			
			# Get the template for this box
			template = properties.get("template", "")
			
			# Set the overrides from the template
			overrides = templates.get(template, {})
			
			# Gets the properties
			# Basic process for each (look up "template system"):
			# 
			#   1. Get template property for if the local property does not 
			#      exist. Also specify a fallback if no such thing is in the 
			#      template.
			# 
			#   2. Get the property if it exsist, otherwise use template, or
			#      if without template, then the fallback paramaters
			# 
			# NOTE: Sorry I just explained how a template system works. It just
			#       something that confused me initially.
			pos = overrides.get("pos", properties.get("pos", "0.0 0.0 0.0"))
			size = overrides.get("size", properties.get("size", "1.0 1.0 1.0"))
			color = overrides.get("color", properties.get("color", "1.0 1.0 1.0"))
			tile = overrides.get("tile", properties.get("tile", "0"))
			tileSize = overrides.get("tileSize", properties.get("tileSize", "1.0 1.0"))
			
			# Convert to numbers
			# Position
			pos = pos.split(" ")
			pos[0] = float(pos[0])
			pos[1] = float(pos[1])
			pos[2] = float(pos[2])
			
			# Size
			size = size.split(" ")
			size[0] = float(size[0])
			size[1] = float(size[1])
			size[2] = float(size[2])
			
			# Colour
			color = color.split(" ")
			color[0] = int(float(color[0]) * 255)
			color[1] = int(float(color[1]) * 255)
			color[2] = int(float(color[2]) * 255)
			if (len(color) == 4):
				color[3] = int(float(color[3]) * 255)
			else:
				color.append(255)
			
			# Tile
			tile = int(tile)
			
			# Tile Size
			tileSize = tileSize.split(" ")
			tileSize[0] = float(tileSize[0])
			tileSize[1] = float(tileSize[1])
			
			add_cube(pos[0], pos[1], pos[2], size[0], size[1], size[2], tile, tileSize[0], tileSize[1], color, light_multiply)
	
	mesh_data = (struct.pack("I", len(mesh_vert) // 24))
	mesh_data += (mesh_vert)
	mesh_data += (struct.pack("I", len(mesh_index) // 12))
	mesh_data += (mesh_index)
	
	mesh_data = zlib.compress(mesh_data)
	
	print(f"Exported {mesh_vert_count} verts.")
	
	mesh.write(mesh_data)
	mesh.close()

#MESHBAKE_END

## IMPORT
## The following things are related to the importer, which is not complete.

def sh_add_box(pos, size):
	bpy.ops.mesh.primitive_cube_add(location = (pos[0], pos[1], pos[2]), scale = (size[0] * 2, size[1] * 2, size[2] * 2))

def sh_add_empty():
	o = bpy.data.objects.new("empty", None)
	
	bpy.context.scene.collection.objects.link(o)
	
	o.empty_display_size = 1
	o.empty_display_type = "PLAIN_AXES"
	
	return o

def sh_import_segment(fp, context, compressed = False):
	root = None
	
	if (not compressed):
		with open(fp, "r") as f:
			root = f.read()
	else:
		with gzip.open(fp, "rb") as f:
			root = f.read().decode()
	
	root = et.fromstring(root)
	
	scene = context.scene.sh_properties
	
	# Segment length
	seg_size = root.attrib.get("size", "12 10 0").split(" ")
	scene.sh_len = float(seg_size[0]), float(seg_size[1]), float(seg_size[2])
	
	# Segment template
	scene.sh_template = root.attrib.get("template", "")
	
	for obj in root:
		kind = obj.tag
		properties = obj.attrib
		
		# Ignore obstacles exported with IMPORT_IGNORE="STONEHACK_IGNORE"
		if (   properties.get("IMPORT_IGNORE") == "STONEHACK_IGNORE"
		    or properties.get("type") == "stone"):
			continue
		
		# Object position
		pos = properties.get("pos", "0 0 0").split(" ")
		pos = float(pos[2]), float(pos[0]), float(pos[1])
		
		# Object rotation
		rot = properties.get("rot", "0 0 0").split(" ")
		rot = float(rot[2]), float(rot[0]), float(rot[1])
		
		# Boxes
		if (kind == "box"):
			# Size for boxes
			size = properties.get("size", "0.5 0.5 0.5").split(" ")
			size = float(size[2]), float(size[0]), float(size[1])
			
			# Boxes can (and often do) have templates
			# o.sh_properties.sh_template = properties.get("template", "")
			
			# Add the box
			sh_add_box(pos, size)
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
			o.sh_properties.sh_mode = properties.get("mode", "0")
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
			color = properties.get("color", "NOCOLOR")
			if (color != "NOCOLOR"):
				o.sh_properties.sh_havetint = True
				color = color.split(" ")
				color = float(color[0]), float(color[1]), float(color[2])
				o.sh_properties.sh_tint = color
			
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
			o = sh_add_empty()
			o.location = pos
			
			# Set the type
			o.sh_properties.sh_type = "WAT"
			
			# Set water size
			size = properties.get("size", "1 1").split(" ")
			o.sh_properties.sh_size = float(size[0]), float(size[1])
			
			# Set hidden
			if (properties.get("hidden", "0") == "1"): o.sh_properties.sh_hidden = True
	
	return {"FINISHED"}

# UI-related

# Uncompressed
class sh_import(bpy.types.Operator, ExportHelper2):
	bl_idname = "sh.import"
	bl_label = "Import Segment"
	
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
		default = (12.0, 10.0, 8.0), 
		min = 0.0,
		max = 750.0
	) 
	
	sh_template: StringProperty(
		name = "Template",
		description = "The template paramater that is passed for the entire segment",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_softshadow: FloatProperty(
		name = "Soft Shadow",
		description = "Exact function unknown, probably shadow transparency",
		default = -0.001,
		min = -0.001,
		max = 1.0
		)
	
	sh_light: FloatVectorProperty(
		name = "Lighting",
		description = "Light intensity, in this order: left, right, top, bottom, front, back",
		default = (1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
		min = 0.0,
		max = 2.0,
		size = 6,
		)
	
	sh_lightfactor: FloatProperty(
		name = "Light Factor",
		description = "Changes the way that light is multiplied so that things do not look too bright",
		default = 0.666,
		min = 0.2,
		max = 1.0
		)

# Object (obstacle/powerup/decal/water) properties

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
	
	sh_obstacle: StringProperty(
		name = "Obstacle",
		description = "Name of the obstacle to be used",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_powerup: EnumProperty(
		name = "Power-up",
		description = "The type of power-up that will appear",
		items = [ ('ballfrenzy', "Ball Frenzy", "Allows the player infinite balls for some time"),
				  ('slowmotion', "Slow Motion", "Slows down the game"),
				  ('nitroballs', "Nitro Balls", "Turns balls into exposlives for a short period of time"),
				  ('barrel', "Barrel", "Creates a large explosion which breaks glass (lefover from beta versions)"),
				],
		default = "ballfrenzy"
		)
	
	sh_export: BoolProperty(
		name = "Export object",
		description = "If the object should be exported to the XML at all. Change \"hidden\" if you'd like it to be hidden but still present in the exported file",
		default = True
		)
	
	sh_hidden: BoolProperty(
		name = "Hidden",
		description = "If the obstacle will show in the level",
		default = False
		)
	
	sh_mode: EnumProperty(
		name = "Mode",
		description = "The game mode that the obstacle will be shown in (This is not currently very correct)",
		items = [ ("0", "All Modes", ""),
				  ("1", "Training", ""),
				  ("2", "Classic", ""),
				  ("3", "Mayhem", ""),
				  ("4", "Zen", ""),
				  ("5", "Versus", ""),
				  ("6", "Co-op", ""),
				],
		default = "0"
		)
	
	##################
	# Mesh properties
	##################
	
	sh_visible: BoolProperty(
		name = "Visible",
		description = "If the box will appear in the exported mesh",
		default = True
		)
	
	sh_tile: IntProperty(
		name = "Tile",
		description = "The texture that will appear on the surface of the box or decal",
		default = 1,
		min = 0,
		max = 63
		)
	
	sh_tilerot: FloatVectorProperty(
		name = "Tile rotation",
		description = "Rotation of the tile, in radians (Pi = 1/2 rotation)",
		default = (0.0, 0.0, 0.0), 
		min = -6.28318530718,
		max = 6.28318530718
	) 
	
	sh_tilesize: FloatVectorProperty(
		name = "Tile size",
		description = "The appearing size of the tiles on the box when exported",
		default = (1.0, 1.0), 
		min = 0.0,
		max = 128.0,
		size = 2
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
	
	sh_tint: FloatVectorProperty(
		name = "Colour",
		description = "The colour to be used for tinting, colouring and mesh data",
		subtype = "COLOR",
		default = (0.5, 0.5, 0.5, 1.0), 
		size = 4,
		min = 0.0,
		max = 1.0
	)
	
	sh_size: FloatVectorProperty(
		name = "Size",
		description = "The size of the object when exported. For boxes this is the tileSize property. In the future, a plain should be used",
		default = (1.0, 1.0), 
		min = 0.0,
		max = 128.0,
		size = 2
	)

class sh_SegmentPanel(Panel):
	bl_label = "Segment Properties"
	bl_idname = "OBJECT_PT_segment_panel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Smash Hit"
	
	@classmethod
	def poll(self, context):
		return context.object is not None
	
	def draw(self, context):
		layout = self.layout
		scene = context.scene
		sh_properties = scene.sh_properties
		
		layout.prop(sh_properties, "sh_len")
		layout.prop(sh_properties, "sh_template")
		layout.prop(sh_properties, "sh_softshadow")
		layout.prop(sh_properties, "sh_light")
		layout.prop(sh_properties, "sh_lightfactor")
		layout.separator()

class sh_ObstaclePanel(Panel):
	bl_label = "Object Properties"
	bl_idname = "OBJECT_PT_obstacle_panel"
	bl_space_type = "VIEW_3D"   
	bl_region_type = "UI"
	bl_category = "Smash Hit"
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
			layout.prop(sh_properties, "sh_obstacle")
		
		# Decal number for decals
		if (sh_properties.sh_type == "DEC"):
			layout.prop(sh_properties, "sh_decal")
		
		# Template for boxes and obstacles
		if (   sh_properties.sh_type == "OBS"
		    or sh_properties.sh_type == "BOX"):
			layout.prop(sh_properties, "sh_template")
		
		# Refelective and tile property for boxes
		if (sh_properties.sh_type == "BOX"):
			layout.prop(sh_properties, "sh_visible")
			if (sh_properties.sh_visible):
				layout.prop(sh_properties, "sh_tile")
				layout.prop(sh_properties, "sh_tilesize")
				layout.prop(sh_properties, "sh_tint")
				layout.prop(sh_properties, "sh_tilerot")
			layout.prop(sh_properties, "sh_reflective")
		
		# Colorization for decals
		if (sh_properties.sh_type == "DEC"):
			layout.prop(sh_properties, "sh_havetint")
			if (sh_properties.sh_havetint):
				layout.prop(sh_properties, "sh_tint")
				layout.prop(sh_properties, "sh_tintalpha")
		
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
			layout.prop(sh_properties, "sh_param0")
			layout.prop(sh_properties, "sh_param1")
			layout.prop(sh_properties, "sh_param2")
			layout.prop(sh_properties, "sh_param3")
			layout.prop(sh_properties, "sh_param4")
			layout.prop(sh_properties, "sh_param5")
			layout.prop(sh_properties, "sh_param6")
			layout.prop(sh_properties, "sh_param7")
			layout.prop(sh_properties, "sh_param8")
			layout.prop(sh_properties, "sh_param9")
			layout.prop(sh_properties, "sh_param10")
			layout.prop(sh_properties, "sh_param11")
		
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
	
	# Add import operators to menu
	bpy.types.TOPBAR_MT_file_import.append(sh_draw_import)
	bpy.types.TOPBAR_MT_file_import.append(sh_draw_import_gz)

def unregister():
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)
	del bpy.types.Scene.sh_properties
