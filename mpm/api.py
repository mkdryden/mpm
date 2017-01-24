# coding: utf-8
'''
See https://github.com/wheeler-microfluidics/microdrop/issues/216
'''
import itertools as it
import json

import conda_helpers as ch


MICRODROP_CONDA_ETC = ch.conda_prefix().joinpath('etc', 'microdrop')
MICRODROP_CONDA_SHARE = ch.conda_prefix().joinpath('share', 'microdrop')


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
