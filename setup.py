import setuptools
import os
import ignis.deploy.version as version

os.chdir(os.path.dirname(__file__))

with open("README.rst", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='ignishpc',
    version=version.__version__,
    author="cesarpomar",
    author_email="cesaralfredo.pineiro@usc.es",
    description='IgnisHPC Deploy',
    long_description=long_description,
    url="https://github.com/ignishpc/deploy",
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux ",
    ],
    install_requires=[
        'docker>=4.1.0',
        'python-hosts>=1.0',
        'GitPython'
    ],
    entry_points={
        'console_scripts': ['ignis-deploy=ignis.deploy.deploy:main'],
    }
)
