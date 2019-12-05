import docker
import os
import shutil
import utils

IMAGE_NAME = "ignishpc/mesos"
MODULE_NAME = "mesos"
CONTAINER_NAME = "ignis-mesos"
CONTAINER_DATA = "/var/lib/ignis/mesos/"


def start(bind, quorum, name, zookeeper, resources, port_master, port_agent, port_chronos, data, docker_bin, force):
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

		if zookeeper is None:
			zookeeper = "zk://" + bind + ":2181"

		if data is None:
			data = CONTAINER_DATA

		if not os.path.exists(data):
			os.makedirs(data)
		elif data is CONTAINER_DATA:
			shutil.rmtree(data)
			os.makedirs(data)

		if docker_bin is None:
			docker_bin = "/usr/local/bin/docker"

		mounts = [
			docker.types.Mount(source=data, target="/var/lib/mesos", type="bind"),
			docker.types.Mount(source="/var/run/docker.sock", target="/var/run/docker.sock", type="bind"),
			docker.types.Mount(source="/cgroup", target="/cgroup", type="bind"),
			docker.types.Mount(source="/sys", target="/sys", type="bind"),
			docker.types.Mount(source=docker_bin, target="/usr/local/bin/docker", type="bind"),
		]

		environment = {
			"MESOS_ADVERSTISE_IP": bind,
			"PORT_MASTER": str(port_master if port_master else 5050),
			"PORT_AGENT": str(port_agent if port_agent else 5051),
			"PORT_CHRONOS": str(port_chronos if port_chronos else 8080),
			"ZOOKEEPER": zookeeper
		}
		if quorum is not None:
			environment["MESOS_QUORUM"] = str(quorum)
		if name is not None:
			environment["MESOS_CLUSTER"] = name
		if resources is not None:
			environment["MESOS_RESOURCES"] = resources

		command = ["/bin/start-mesos.sh"]

		container = client.containers.run(
			image=IMAGE_NAME,
			name=CONTAINER_NAME,
			detach=True,
			environment=environment,
			privileged=True,
			command=command,
			mounts=mounts,
			network_mode="host"
		)

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
