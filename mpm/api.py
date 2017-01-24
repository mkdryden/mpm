# coding: utf-8
'''
See https://github.com/wheeler-microfluidics/microdrop/issues/216
'''
import itertools as it
import json
import types

import conda_helpers as ch


MICRODROP_CONDA_ETC = ch.conda_prefix().joinpath('etc', 'microdrop')
MICRODROP_CONDA_SHARE = ch.conda_prefix().joinpath('share', 'microdrop')
MICRODROP_CONDA_ACTIONS = MICRODROP_CONDA_ETC.joinpath('actions')


def _channel_args(channels=None):
    '''
    Parameters
    ----------
    channels : list, optional
        List of Conda channels.

    Returns
    -------
    list
        List of arguments to pass to Conda commands to specify channels.

        For example, ``['-c', 'wheeler-plugins', '-c', 'conda-forge']``.
    '''
    channels = channels or ['microdrop-plugins']
    return list(it.chain(*[['-c', c] for c in channels]))


def _save_action(extra_context=None):
    '''
    Save list of revisions revisions for active Conda environment.

    Parameters
    ----------
    extra_context : dict, optional
        Extra content to store in stored action revision.

    Returns
    -------
    path_helpers.path, dict
        Path to which action was written and action object, including list of
        revisions for active Conda environment.
    '''
    # Get list of revisions to Conda environment since creation.
    revisions_js = ch.conda_exec('list', '--revisions', '--json',
                                 verbose=False)
    revisions = json.loads(revisions_js)
    # Save list of revisions to `/etc/microdrop/plugins/actions/rev<rev>.json`
    # See [wheeler-microfluidics/microdrop#200][i200].
    #
    # [i200]: https://github.com/wheeler-microfluidics/microdrop/issues/200
    action = extra_context.copy() if extra_context else {}
    action['revisions'] = revisions
    action_path = (MICRODROP_CONDA_ACTIONS
                   .joinpath('rev{}.json'.format(revisions[-1]['rev'])))
    action_path.parent.makedirs_p()
    with action_path.open('w') as output:
        json.dump(action, output, indent=2)
    return action_path, action


# ## Supporting legacy MicroDrop plugins ##
#
# Legacy MicroDrop plugins **MAY** be made **available** by linking according
# to **(2)** above.
#
# # TODO #
#
#  - [ ] Create Python API for MicroDrop plugins to:
#      * [x] Query available plugin packages based on specified Conda channels
def available_packages(channels=None):
    '''
    Query available plugin packages based on specified Conda channels.

    Parameters
    ----------
    channels : list, optional
        List of Conda channels to search.

        Local channels can be specified using the ``'file://'`` prefix.

        For example, on Windows, use something similar to:

            'file:///C:/Users/chris/local-repo'

        ..notes::
            A local directory containing packages may be converted to a local
            channel by running ``conda index`` within the directory.

            Each local file channel must point to a directory with the name of
            a Conda platform (e.g., ``win-32``) or to a parent directory
            containing multiple directories, where each directory has the name
            of a Conda platform.

    Returns
    -------
    dict
        All available packages from channels.

        Each *key* corresponds to a package name.

        Each *value* corresponds to a ``list`` of dictionaries, each
        corresponding to an available version of the respective package.
    '''
    channels_args = _channel_args(channels)

    # Get dictionary of available packages
    conda_args = ['search', '--override-channels', '--json'] + channels_args
    pkgs_js = ch.conda_exec(*conda_args, verbose=False)
    return json.loads(pkgs_js)


#      * [x] Install plugin package(s) from selected Conda channels
def install(plugin_name, *args, **kwargs):
    '''
    Install plugin packages based on specified Conda channels.

    Parameters
    ----------
    plugin_name : str or list
        Plugin package(s) to install.

        Version specifiers are also supported, e.g., ``package >=1.0.5``.
    *args
        Extra arguments to pass to Conda ``install`` command.
    channels : list, optional
        List of Conda channels to search.

        Local channels can be specified using the ``'file://'`` prefix.

        For example, on Windows, use something similar to:

            'file:///C:/Users/chris/local-repo'

        ..notes::
            A local directory containing packages may be converted to a local
            channel by running ``conda index`` within the directory.

            Each local file channel must point to a directory with the name of
            a Conda platform (e.g., ``win-32``) or to a parent directory
            containing multiple directories, where each directory has the name
            of a Conda platform.

    Returns
    -------
    dict
        Result from

        Each *key* corresponds to a package name.

        Each *value* corresponds to a ``list`` of dictionaries, each
        corresponding to an available version of the respective package.
    '''
    channel_args = _channel_args(channels=kwargs.pop('channels', None))
    if isinstance(plugin_name, types.StringTypes):
        plugin_name = [plugin_name]

    # Perform installation
    conda_args = (['install', '-y', '--json'] + channel_args + list(args) +
                  plugin_name)
    install_log_js = ch.conda_exec(*conda_args, verbose=False)
    install_log = json.loads(install_log_js.split('\x00')[-1])
    if 'actions' in install_log:
        # Install command modified Conda environment.
        _save_action({'conda_args': conda_args, 'install_log': install_log})
    return install_log
