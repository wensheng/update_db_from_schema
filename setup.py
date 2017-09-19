"""
yml2db setup.py
"""

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='yml2db',
    version='0.2',
    description='Update database by changing schema yaml file',
    long_description=long_description,
    url='https://github.com/wensheng/yml2db',
    author='Wensheng Wang',
    author_email='wenshengwang@gmail.com',
    license='MIT',

    classifiers=[
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development',
        'Topic :: Database',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],

    keywords='database schema mysql postgresql yaml',
    packages=find_packages(exclude=['docs', 'tests']),
    install_requires=['pyyaml', 'pymysql'],

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={
        'yml2db': ['db_config.ini.sample'],
    },

    entry_points={
        'console_scripts': [
            'yml2db=yml2db:main',
        ],
    }
)
