import logging
import os
import subprocess as sp
import sys

import path_helpers as ph


logger = logging.getLogger(__name__)


def on_plugin_install(plugin_directory, ostream=sys.stdout):
    '''
    Run ``on_plugin_install`` script for specified plugin directory (if
    available).

    **TODO** Add support for Linux, OSX.

    Parameters
    ----------
    plugin_directory : str
        File system to plugin directory.
    ostream :file-like
        Output stream for status messages (default: ``sys.stdout``).
    '''
    current_directory = os.getcwd()

    plugin_directory = ph.path(plugin_directory).realpath()
    print >> ostream, ('Processing post-install hook for: '
                        '{}'.format(plugin_directory.name))

    hooks_dir_i = plugin_directory.joinpath('hooks/Windows').realpath()
    hook_path_i = hooks_dir_i.joinpath('on_plugin_install.bat')

    if hook_path_i.isfile():
        logger.info('Processing post-install hook for: %s',
                    plugin_directory.name)
        os.chdir(hook_path_i.parent)
        try:
            sp.check_call([hook_path_i, sys.executable], shell=True)
            return hook_path_i
        except:
            raise RuntimeError('Error running: {}'.format(hook_path_i))
        finally:
            os.chdir(current_directory)
