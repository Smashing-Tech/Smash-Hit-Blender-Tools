# Contributing

Thank you for helping make Smash Hit Blender Tools better! :)

## Main notes

We don't have much a formal policy surrounding contributions. However, here are some helpful notes:

1. There is currently no naming scheme that is strictly followed; however, it is recommended that you use:
	* `camelCase` for function names
	* `PascalCase` for class names
	* `snake_case` for variable names
	* `CAPITAL_SNAKE_CASE` for names of constants
2. The large features are generally split into modules of their own, in addition to segment import/export operations.
3. The mesh baker and quick test server should remain somewhat seprate modules from Blender Tools. They should be able to be run on their own.

## Modules

* The `blender_tools` module is the main module.
* The `common` module should contain any constants, including `bl_info`.
* Any configuration or non-temporary, non-output files should use `common.TOOLS_HOME_FOLDER`.