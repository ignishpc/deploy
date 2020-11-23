import docker
import utils

IMAGE_NAME = "ignishpc/submitter"
MODULE_NAME = "submitter"
CONTAINER_NAME = "ignis-submitter"


def start(port, dfs, dfs_home, password, scheduler, shceduler_url, dns, default_registry, force):
	try:
		client = docker.from_env()
		container = utils.getContainer(client, CONTAINER_NAME)
		if container:
			if force:
				container.remove(force=True)
			else:
				print("error: " + CONTAINER_NAME + " already exists")
				exit(-1)

		if port is None:
			port = 2222

		if password is None:
			password = "ignis"

		if dfs_home is None:
			dfs_home = "/media/dfs"

		mounts = [
			docker.types.Mount(source=dfs, target="/media/dfs", type="bind"),
		]

		environment = {
			"IGNIS_DFS_ID": dfs,
			"IGNIS_DFS_HOME": dfs_home,
			"IGNIS_SCHEDULER_TYPE": scheduler,
			"IGNIS_SCHEDULER_URL": shceduler_url,
		}

		if dns:
			mounts.append(docker.types.Mount(source="/etc/hosts", target="/etc/hosts", type="bind", read_only=True))
			environment["IGNIS_SCHEDULER_DNS"] = "host"

		if default_registry:
			environment["IGNIS_REGISTRY"] = default_registry

		container_ports = {
			"22": str(port)
		}

		command = ["/opt/ignis/bin/ignis-sshd"]

		container = client.containers.run(
			image=default_registry+IMAGE_NAME,
			name=CONTAINER_NAME,
			detach=True,
			environment=environment,
			command=command,
			mounts=mounts,
			ports=container_ports
		)

		container.exec_run(["bash", "-c", 'echo "root:' + password + '" | chpasswd'])

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
