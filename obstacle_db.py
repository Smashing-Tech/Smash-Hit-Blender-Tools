import pathlib

# For obstacle picker
OBSTACLES = [
	("boss/cube", "Boss: Cube", ""),
	("boss/matryoshka", "Boss: Matryoshka", ""),
	("boss/single", "Boss: Single", ""),
	("boss/telecube", "Boss: Telecube", ""),
	("boss/triple", "Boss: Triple", ""),
	None,
	("doors/45", "Door: 45", ""),
	("doors/basic", "Door: Basic", ""),
	("doors/double", "Door: Double", ""),
	None,
	("fence/carousel", "Fence: Carousel", ""),
	("fence/dna", "Fence: Dna", ""),
	("fence/slider", "Fence: Slider", ""),
	None,
	("scoretop", "Crystal: Payramid (+3)", ""),
	("scorediamond", "Crystal: Diamond (+5)", ""),
	("scorestar", "Crystal: Star (+10)", ""),
	("scoremulti", "Crystal: Transcendal", ""),
	None,
	("3dcross", "3D cross", ""),
	("creditssign", "Credits sign", ""),
	("hitblock", "Hit block", ""),
	("suspendcube", "Suspsended cube", ""),
	("babytoy", "Baby toy", ""),
	("cubeframe", "Cube frame", ""),
	("laser", "Laser", ""),
	("suspendcylinder", "Suspsended cylinder", ""),
	("bar", "Bar", ""),
	("dna", "Dna", ""),
	("levicube", "Jumping cube", ""),
	("suspendhollow", "Suspended rombahidria", ""),
	("beatmill", "Beat mill", ""),
	("ngon", "N-gon shape", ""),
	("suspendside", "Suspended sweeper", ""),
	("beatsweeper", "Beat sweeper", ""),
	("dropblock", "Drop block", ""),
	("pyramid", "Cube pyramid", ""),
	("suspendwindow", "Suspended window", ""),
	("beatwindow", "Beat window", ""),
	("elevatorgrid", "Elevator grid", ""),
	("revolver", "Revolver", ""),
	("sweeper", "Sweeper", ""),
	("bigcrank", "Big crank", ""),
	("elevator", "Elevator", ""),
	("rotor", "Rotor", ""),
	("test", "Test obstacle", ""),
	("bigpendulum", "Pendulum (hammer)", ""),
	("tree", "Tree", ""),
	("flycube", "Flying cube", ""),
	("vs_door", "Verus door", ""),
	("bowling", "Bowling row", ""),
	("foldwindow", "Folding window", ""),
	("vs_sweeper", "Versus sweeper", ""),
	("box", "Box", ""),
	("framedwindow", "Framed window", ""),
	("vs_wall", "Versus wall", ""),
	("cactus", "Cactus", ""),
	("gear", "Gear", ""),
	("sidesweeper", "Side sweeper", ""),
	("credits1", "Credits obstacle 1", ""),
	("grid", "Grid", ""),
	("stone", "Stone", ""),
	("credits2", "Credits obstacle 2", ""),
	("gyro", "Gyro", ""),
	("suspendbox", "Suspended box", ""),
	None,
]

# For search in free-form entry
OBSTACLES_LIST = ["3dcross", "babytoy", "bar", "beatmill", "beatsweeper", "beatwindow", "bigcrank", "bigpendulum", "boss", "bowling", "box", "cactus", "credits1", "credits2", "creditssign", "cubeframe", "dna", "doors", "dropblock", "elevatorgrid", "elevator", "fence", "flycube", "foldwindow", "framedwindow", "gear", "grid", "gyro", "hitblock", "laser", "levicube", "ngon", "pyramid", "revolver", "rotor", "scorediamond", "scoremulti", "scorestar", "scoretop", "sidesweeper", "stone", "suspendbox", "suspendcube", "suspendcylinder", "suspendhollow", "suspendside", "suspendwindow", "sweeper", "test", "tree", "vs_door", "vs_sweeper", "vs_wall", "boss/cube", "boss/matryoshka", "boss/single", "boss/telecube", "boss/triple", "doors/45", "doors/basic", "doors/double", "fence/carousel", "fence/dna", "fence/slider"]

# Find custom obstacles
try:
	with open(str(pathlib.Path.home()) + "/smash-hit-obstacles.txt", "r") as f:
		content = f.read()
		content = content.split("\n")
		
		for obs in content:
			s = obs.split("=")
			
			if (len(s) == 2 and not s[0].startswith("#")):
				OBSTACLES.append((s[0], s[1], ""))
				OBSTACLES_LIST.append(s[0])
except FileNotFoundError:
	print("Smash Hit Blender Tools: " + str(__name__) + ": Could not find text file for custom obstacles!")
