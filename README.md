# Smash Hit Tools for Blender

**Smash Hit Tools for Blender** is an addon for Blender that allows the creation of segments (parts of levels) for the mobile game *Smash Hit*. Currently, it can handle boxes, obstacles, decals and water to the degree that it should be possible to create segments which look official.

## Help

Please see [the wiki](https://github.com/knot126/Smash-Hit-Blender-Tools/wiki) for information about how to use the addon, as well as some technical information about Smash Hit and the mesh baker.

## Modules

### Mesh baker

*[`bake_mesh.py`](bake_mesh.py)*

Contains a script to bake a mesh. It is usually used as part of SHBT, though it can also be used by itself.

Usage from CLI:

```sh
$ python ./bake_mesh.py (input) (output) [optional: template file] 
```

### Obstacle DB

*[`obstacle_db.py`](obstacle_db.py)*

This contains a very basic obstacle database. It can also load a text file that contains a list of custom obstacles.

### Server

*[`server.py`](server.py)*

This is the quick test server module. It contains the HTTP server that Smash Hit can load files from.

### Updater

*[`updater.py`](updater.py)*

This contains a script to check if Blender Tools is up to date, and pop up a message if it is not.