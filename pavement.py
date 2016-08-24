import sys

from paver.easy import task, needs, path, sh, cmdopts, options
from paver.setuputils import setup, install_distutils_tasks
from distutils.extension import Extension
from distutils.dep_util import newer

sys.path.insert(0, path('.').abspath())
import version

setup(name='microdrop-plugin-manager',
      version=version.getVersion(),
      description='Microdrop plugin manager.',
      keywords='',
      author='Christian Fobel',
      author_email='christian@fobel.net',
      url='https://github.com/wheeler-microfluidics/mpm',
      license='LGPLv2.1',
      packages=['mpm', ],
      install_requires=['configobj', 'path-helpers', 'pip-helpers>=0.6',
                        'progressbar2', 'pyyaml', 'si-prefix>=0.4.post3'],
      # Install data listed in `MANIFEST.in`
      include_package_data=True,
      entry_points = {'console_scripts': ['mpm = mpm.bin:main']})


@task
@needs('generate_setup', 'minilib', 'setuptools.command.sdist')
def sdist():
    """Overrides sdist to make sure that our setup.py is generated."""
    pass
