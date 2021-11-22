import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='ignishpc',
    version='2.0.1',
    author="cesarpomar",
    author_email="cesaralfredo.pineiro@usc.es",
    description='Ignis deploy script',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/ignis-hpc/deploy",
    packages=setuptools.find_packages(),
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
