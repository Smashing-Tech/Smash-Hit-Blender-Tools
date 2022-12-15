"""
Smash Hit segment export tool for Blender - main file

This mostly handles UI stuff
"""

import common

SH_MAX_STR_LEN = common.MAX_STRING_LENGTH
bl_info = {
	"name": "Smash Hit Tools",
	"description": "Segment exporter and property editor for Smash Hit",
	"author": "Smashing Tech",
	"version": (2, 0, 18),
	"blender": (3, 2, 0),
	"location": "File > Import/Export and 3D View > Tools",
	"warning": "",
	"wiki_url": "https://github.com/Smashing-Tech/Smash-Hit-Blender-Tools/wiki",
	"tracker_url": "https://github.com/Smashing-Tech/Smash-Hit-Blender-Tools/issues",
	"category": "Development",
}

import xml.etree.ElementTree as et
import bpy
import gzip
import tempfile
import obstacle_db
import segment_export
import segment_import
import server
import updater

from bpy.props import (StringProperty, BoolProperty, IntProperty, IntVectorProperty, FloatProperty, FloatVectorProperty, EnumProperty, PointerProperty)
from bpy.types import (Panel, Menu, Operator, PropertyGroup, AddonPreferences)

# The name of the test server. If set to false initially, the test server will
# be disabled.
g_process_test_server = True

class sh_ExportCommon(bpy.types.Operator, segment_export.ExportHelper2):
	"""
	Common code and values between export types
	"""
	
	def __init__(self):
		"""
		Automatic templates.xml detection
		"""
		
		if (not self.sh_meshbake_template):
			self.sh_meshbake_template = segment_export.tryTemplatesPath()
	
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
		
		result = segment_export.sh_export_segment(
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
		
		result = segment_export.sh_export_segment(
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
		
		result = segment_export.sh_export_segment(
			None,
			context,
			params = {
				"sh_vrmultiply": sh_properties.sh_vrmultiply,
				"sh_box_bake_mode": sh_properties.sh_box_bake_mode,
				"bake_menu_segment": sh_properties.sh_menu_segment,
				"bake_vertex_light": sh_properties.sh_ambient_occlusion,
				"lighting_enabled": sh_properties.sh_lighting,
				"sh_test_server": True,
				"sh_meshbake_template": segment_export.tryTemplatesPath()
			}
		)
		
		return result

def sh_draw_export_test(self, context):
	self.layout.operator("sh.export_test_server", text="SHBT Quick Test Server")

# UI-related

class sh_import(bpy.types.Operator, segment_export.ExportHelper2):
	"""
	Import for uncompressed segments
	"""
	
	bl_idname = "sh.import"
	bl_label = "Import Segment"
	
	check_extension = False
	filename_ext = ".xml.mp3"
	filter_glob = bpy.props.StringProperty(default='*.xml.mp3', options={'HIDDEN'}, maxlen=255)
	
	def execute(self, context):
		return segment_import.sh_import_segment(self.filepath, context)

def sh_draw_import(self, context):
	self.layout.operator("sh.import", text="Segment (.xml.mp3)")

class sh_import_gz(bpy.types.Operator, segment_export.ExportHelper2):
	"""
	Import for compressed segments
	"""
	
	bl_idname = "sh.import_gz"
	bl_label = "Import Compressed Segment"
	
	check_extension = False
	filename_ext = ".xml.gz.mp3"
	filter_glob = bpy.props.StringProperty(default='*.xml.gz.mp3', options={'HIDDEN'}, maxlen=255)
	
	def execute(self, context):
		return segment_import.sh_import_segment(self.filepath, context, True)

def sh_draw_import_gz(self, context):
	self.layout.operator("sh.import_gz", text="Compressed Segment (.xml.gz.mp3)")

## EDITOR
## The following things are more related to the editor and are not specifically
## for exporting or importing segments.

class sh_SceneProperties(PropertyGroup):
	"""
	Segment (scene) properties
	"""
	
	sh_level: StringProperty(
		name = "Level name",
		description = "The name of the checkpoint that this segment belongs to. The checkpoints will go in alphabetical order, so it's recommended to prefix with 0_, 1_, 2_, etc",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_room: StringProperty(
		name = "Room name",
		description = "The name of the room that this segment belongs to. The rooms will go in alphabetical order, so it's recommended to prefix with 0_, 1_, 2_, etc",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
	sh_segment: StringProperty(
		name = "Segment name",
		description = "The name of this segment. You don't need to prefix this because the order will be random",
		default = "",
		maxlen = SH_MAX_STR_LEN,
		)
	
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
		default = 0.8,
		min = 0.0,
		max = 1.0,
		)
	
	sh_light_right: FloatProperty(
		name = "Right",
		description = "Light going on to the right side of boxes",
		default = 0.85,
		min = 0.0,
		max = 1.0,
		)
	
	sh_light_top: FloatProperty(
		name = "Top",
		description = "Light going on to the top side of boxes",
		default = 0.9,
		min = 0.0,
		max = 1.0,
		)
	
	sh_light_bottom: FloatProperty(
		name = "Bottom",
		description = "Light going on to the bottom side of boxes",
		default = 0.75,
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
	
	# Yes, I'm trying to add "DRM" support for this. It can barely be called that
	# but I think it would fit the definition of DRM, despite not being very
	# strong. This isn't available in the UI for now to emphasise that it's not
	# really that useful.
	sh_drm_disallow_import: BoolProperty(
		name = "Disallow import",
		description = "This will disallow importing the exported segment. It can very easily be bypassed, but might prevent a casual user from editing your segment without asking. Please use this feature wisely and consider providing Blender files for people who ask nicely",
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
		description = "The size of the object when exported",
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

class sh_AddonPreferences(AddonPreferences):
	bl_idname = "blender_tools"
	
	enable_update_notifier: BoolProperty(
		name = "Enable update notifier",
		description = "Enables the update notifier. This will try to contact github, which may pose a privacy risk",
		default = True,
	)
	
	enable_auto_update: BoolProperty(
		name = "Enable automatic updates",
		description = "Automatically downloads the newest version of Blender Tools. You still need to install it manually, and you should still check the website to make sure SHBT has not been cracked/hacked",
		default = False,
	)
	
	enable_quick_test_server: BoolProperty(
		name = "Enable quick test server",
		description = "Enables the quick test server. This will create a local http server using python, which might pose a security risk",
		default = True,
	)
	
	def draw(self, context):
		ui = self.layout
		
		ui.label(text = "Network and privacy settings")
		ui.prop(self, "enable_update_notifier")
		if (self.enable_update_notifier):
			ui.prop(self, "enable_auto_update")
			if (self.enable_auto_update):
				box = ui.box()
				# box.label(icon = "ERROR", text = "Enabling the automatic updater means you won't be able to check that something contains a virus. We do not have the same security measures as other software to make sure that the software is coming from trusted developers. Please don't enable this option if you don't actually understand the risks.")
				box.label(icon = "ERROR", text = "It's not recommended to enable this. Autoupdate is insecure.")
		ui.prop(self, "enable_quick_test_server")

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
		
		# layout.prop(sh_properties, "sh_level")
		# layout.prop(sh_properties, "sh_room")
		# layout.prop(sh_properties, "sh_segment")
		
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
		layout.prop(sh_properties, "sh_drm_disallow_import")
		
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
			
			# Properties affected by being visible
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
			
			# Box Transformations
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

def run_updater():
	try:
		global bl_info
		updater.check_for_updates(bl_info["version"])
	except Exception as e:
		print(f"Smash Hit Tools: updater.check_for_updates(): {e}")

classes = (
	# Ignore the naming scheme for classes, please
	sh_SceneProperties,
	sh_EntityProperties,
	sh_SegmentPanel,
	sh_ObstaclePanel,
	sh_AddonPreferences,
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
	
	if (g_process_test_server and bpy.context.preferences.addons["blender_tools"].preferences.enable_quick_test_server):
		g_process_test_server = server.runServerProcess()
	
	# Check for updates
	run_updater()

def unregister():
	from bpy.utils import unregister_class
	
	for cls in reversed(classes):
		unregister_class(cls)
	
	del bpy.types.Scene.sh_properties
	
	# Shutdown server
	global g_process_test_server
	
	if (g_process_test_server):
		g_process_test_server.terminate()
