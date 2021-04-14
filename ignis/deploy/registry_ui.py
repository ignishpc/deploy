import sys

import docker

import ignis.deploy.utils as utils

IMAGE_NAME = "joxit/docker-registry-ui:1.5-static"
MODULE_NAME = "registry-ui"
CONTAINER_NAME = "ignis-registry-ui"


def start(bind, port, registry, force):
	try:
		client = docker.from_env()
		container = utils.getContainer(client, CONTAINER_NAME)
		if container:
			if force:
				container.remove(force=True)
			else:
				print("error: " + CONTAINER_NAME + " already exists")
				exit(-1)

		if bind is None:
			bind = utils.getHostname()
			print("info: " + bind + " selected for internal cluster communications, use --bind to select another")

		if port is None:
			port = 3000

		container_ports = {
			"80": str(port)
		}

		if registry.startswith("http"):
			import urllib.parse
			parsed = urllib.parse.urlparse(registry)
			host_port = parsed.netloc.split(":")
			host_port[0] = utils.getIpAddress(host_port[0])
			parsed = parsed._replace(netloc=':'.join(host_port))
			url = urllib.parse.urlunparse(parsed)
		else:
			host_port = registry.split(":")
			host_port[0] = utils.getIpAddress(host_port[0])
			url = "http://" + ':'.join(host_port)

		if url.endswith("/"):
			url = url[:-1]

		environment = {
			"REGISTRY_URL": url,
			"DELETE_IMAGES": "true",
			"REGISTRY_TITLE": "Ignis"
		}

		container = client.containers.run(
			image=IMAGE_NAME,
			name=CONTAINER_NAME,
			detach=True,
			environment=environment,
			ports=container_ports
		)

	except PermissionError:
		print("root required!!", file=sys.stderr)
		sys.exit(-1)
	except Exception as ex:
		print("error:  " + str(ex))
		exit(-1)


def status():
	client = docker.from_env()
	return utils.getStatus(client, CONTAINER_NAME)


def resume():
	client = docker.from_env()
	utils.containerAction(client, CONTAINER_NAME, MODULE_NAME, lambda container: container.start())


def stop():
	client = docker.from_env()
	utils.containerAction(client, CONTAINER_NAME, MODULE_NAME, lambda container: container.stop())


def destroy():
	client = docker.from_env()
	utils.containerAction(client, CONTAINER_NAME, MODULE_NAME, lambda container: container.remove(force=True))
