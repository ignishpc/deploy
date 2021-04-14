import docker

import ignis.deploy.utils as utils

IMAGE_NAME = "ignishpc/glusterfs"
MODULE_NAME = "glusterfs"
CONTAINER_NAME = "ignis-glusterfs"


def start():
    raise NotImplementedError("glusterfs not implemented")


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
