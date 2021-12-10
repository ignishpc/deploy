import sys

import docker

import ignis.deploy.utils as utils

IMAGE_NAME = "registry:2.7.1"
MODULE_NAME = "registry"
CONTAINER_NAME = "ignis-registry"
DEFAULT = "IGNIS_REGISTRY_DEFAULT"
URL = "IGNIS_REGISTRY"


def start(bind, port, path, default, clear, force):
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
		port = 5000

	if path is None:
		path = "/var/lib/ignis/registry"

	if clear:
		utils.rmIfExists(path)
	utils.mkdirIfNotExists(path)

	mounts = [
		docker.types.Mount(source=path, target="/var/lib/registry", type="bind"),
	]

	labels = {
		URL: bind + ":" + str(port),
		DEFAULT: str(default),
	}

	container_ports = {
		"5000": str(port)
	}

	environment = {
		"REGISTRY_STORAGE_DELETE_ENABLED": "true"
	}

	container = client.containers.run(
		image=IMAGE_NAME,
		name=CONTAINER_NAME,
		detach=True,
		environment=environment,
		labels=labels,
		mounts=mounts,
		ports=container_ports
	)

	print('info: add \'{insecure-registries" : [ "' + bind + ":" + str(
		port) + '" ]}\' to /etc/docker/daemon.json and restart docker daemon service')
	print("      use " + bind + ":" + str(port) + " to refer the registry")


def garbage():
	try:
		client = docker.from_env()
		container = utils.getContainer(client, CONTAINER_NAME)
		if not container:
			print(CONTAINER_NAME + " is not RUNNING", file=sys.stderr)
			exit(-1)
		container.exec_run(["bin/registry", "garbage-collect" "/etc/docker/registry/config.yml"])

	except PermissionError:
		print("root required!!", file=sys.stderr)
		sys.exit(-1)
	except Exception as ex:
		print("error:  " + str(ex), file=sys.stderr)
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


def parse(r):
	if r is None:
		r = ""
		client = docker.from_env()
		container = utils.getContainer(client, CONTAINER_NAME)
		if container:
			if DEFAULT in container.labels:
				r = container.labels[URL]
	if r and r[-1] != '/':
		return r + "/"
	return r
