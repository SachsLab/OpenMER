from setuptools import setup, find_packages
from os import path


package_name = "neuroport_dbs"
here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Get the version number from the version file
# Versions should comply with PEP440.  For a discussion on single-sourcing
# the version across setup.py and the project code, see
# https://packaging.python.org/en/latest/single_source_version.html
with open(path.join(package_name, "version.py")) as f:
    exec(f.read())  # Sets __version__ in setup namespace


setup(
    name=package_name,
    version=__version__,
    packages=find_packages(),
    data_files=[('icons', ['neuroport_dbs/icons/depth_status_done.png',
                           'neuroport_dbs/icons/depth_status_in_use.png',
                           'neuroport_dbs/icons/depth_status_off.png'])],
    
    description='Tools for clinical research using Blackrock Neurport in DBS MER',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Chadwick Boulay',
    author_email='chadwick.boulay@gmail.com',
    maintainer='Guillaume Doucet',
    maintainer_email='gudoucet@ohri.ca',
    url='https://github.com/SachsLab/NeuroportDBS',
    license='GPL v3',

    entry_points={
        'gui_scripts': ['dbs-sweep=neuroport_dbs.SweepGUI:main',
                        'dbs-waveform=neuroport_dbs.WaveformGUI:main',
                        'dbs-raster=neuroport_dbs.RasterGUI:main',
                        'dbs-features=neuroport_dbs.FeaturesGUI:main',
                        'dbs-comments=neuroport_dbs.CommentsGUI:main',
                        'dbs-ddu=neuroport_dbs.DDUGUI:main',
                        ],
    }
)
