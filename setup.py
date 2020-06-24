from setuptools import setup, find_packages
from pip.req import parse_requirements

with open("README.md") as f:
    readme = f.read()

setup(
    name="jnrr",
    version="0.0.1",
    description=("jnnr is a tool for joint-non-rigid-image-registration"),
    url='https://github.com/din14970/TEMMETA',
    author='Niels Cautaerts',
    author_email='nielscautaerts@hotmail.com',
    license='GPL-3.0',
    long_description=readme,
    long_description_content_type="text/markdown",
    classifiers=['Topic :: Scientific/Engineering :: Physics',
                 'Intended Audience :: Science/Research',
                 'Operating System :: OS Independent',
                 'Programming Language :: Python :: 3.7',
                 'Programming Language :: Python :: 3.8'],
    keywords='TEM',
    packages=find_packages(exclude=["*tests*", "*examples*", "*data*"]),
    install_requires=parse_requirements('requirements.txt', session='hack')
)