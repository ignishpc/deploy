import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
	name='ignis-deploy',
	version='1.0',
	description='Ignis deploy script',
	long_description=long_description,
	long_description_content_type="text/markdown",
	packages=setuptools.find_packages(),
	install_requires=['docker>=4.1.0', 'python-hosts>=1.0'],
	entry_points = {
		'console_scripts': ['ignis-deploy=ignis.deploy.deploy:cli'],
	}
)
