"""uWeb3 warehouse installer."""

import os
import re
from setuptools import setup, find_packages

REQUIREMENTS = [
  'passlib'
]

def description():
  """Returns the contents of the README.md file as description information."""
  with open(os.path.join(os.path.dirname(__file__), 'README.md')) as r_file:
    return r_file.read()


def version():
  """Returns the version of the library as read from the __init__.py file"""
  main_lib = os.path.join(os.path.dirname(__file__), 'base', '__init__.py')
  with open(main_lib) as v_file:
    return re.match(".*__version__ = '(.*?)'", v_file.read(), re.S).group(1)


setup(
    name='uWeb3 warehouse',
    version=version(),
    description='uWeb, python3, uswgi compatible warehousing app',
    long_description_file='README.md',
    long_description_content_type='text/markdown',
    license='ISC',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',

        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Operating System :: POSIX :: Linux',
    ],
    author='Jan Klopper',
    author_email='jan@underdark.nl',
    url='https://github.com/underdark.nl/warehouse',
    keywords='hwarehouseing software based on uWeb3',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=REQUIREMENTS)
