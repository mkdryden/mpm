![https://ci.appveyor.com/api/projects/status/github/wheeler-microfluidics/mpm?branch=master&svg=true](https://ci.appveyor.com/api/projects/status/github/wheeler-microfluidics/mpm?branch=master&svg=true)
Microdrop plugin manager inspired by ``pip``.

------------------------------------------------------------------------

Installation
============

Install using `pip`:

    pip install microdrop-package-manager

------------------------------------------------------------------------

Usage
=====

    mpm install <plugin-name>[(==|>|>=|<=)version] [<plugin-name>[(==|>|>=|<=)version]...]
    mpm install -r plugin_requirements.txt
    mpm uninstall <plugin-name>
    mpm freeze
    mpm --help  # Display detailed usage information

Use `mpm --help` for detailed usage information.

Common flags
------------

`-l, --log-level`: Logging level (`error, debug, info`).

`-c, --config-file`: Microdrop config file (default= `<Documents>\Microdrop\microdrop.ini`).

`-d, --plugins-directory`: Microdrop plugins directory (default= `<Documents>\Microdrop\plugins`).

Note that the `--config-file`/`--plugins-directory` flags are used to locate the plugins directory to operate on.

If the `--config-file` flag is used, the plugin directory is read from the configuration file (relative paths are considered relative to the location of the configuration file).

The `--plugins-directory` flag sets the plugins directory explicitly.

`mpm install` flags
-------------------

`-s, --server-url`: Microdrop plugin index URL (default= `http://microfluidics.utoronto.ca/update`)

`--no-on-install`: Do not run `on_plugin_install` hook after installing plugin

`-r, --requirements-file`: Requirements file (one line per plugin version descriptor)

`mpm search` flags
------------------

`-s, --server-url`: Microdrop plugin index URL (default= `http://microfluidics.utoronto.ca/update`)

------------------------------------------------------------------------

Examples
========

Install `dmf_control_board`:

    mpm install dmf_control_board

Install specific version of `dmf_control_board`:

    mpm install "dmf_control_board==1.1.0"

Uninstall `dmf_control_board`:

    mpm uninstall dmf_control_board

Install plugin from archive file:

    mpm install dmf_control_board-1.1.0.tar.gz

Print list of installed plugins:

    mpm freeze

------------------------------------------------------------------------

Documentation
=============

Documentation is available online [here][1] .

------------------------------------------------------------------------

Development
===========

Project is hosted on [GitHub][2] .


[1]: http://microdrop-plugin-manager.readthedocs.io
[2]: https://github.com/wheeler-microfluidics/mpm
