import os
import sys

import docker

import ignis.deploy.utils as utils

MESOS_IMAGE_NAME = "mesos-base"
MARATHON_IMAGE_NAME = "mesos-marathon"
SINGULARITY_IMAGE_NAME = "mesos-singularity"
MODULE_NAME = "mesos"
CONTAINER_NAME = "ignis-mesos"
CONTAINER_DATA = "/var/lib/ignis/mesos/"
SINGULARITY_LOG = "/var/log/ignis/singularity/"
SINGULARITY_CONF = "/etc/ignis/singularity/"
RESOURCES = os.path.join(os.path.dirname(os.path.realpath(__file__)), "resources")


def start(service, bind, quorum, name, zookeeper, resources, port_master, port_agent, port_service, no_agent, data,
          docker_bin, url_namespace, img_tag, clear, force):
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
    data = os.path.normpath(data)
    if clear:
        utils.rmIfExists(data)

    utils.mkdirIfNotExists(data)

    if docker_bin is None:
        docker_bin = "/usr/bin/docker"

    mounts = [
        docker.types.Mount(source=data, target=data, type="bind"),
        docker.types.Mount(source="/var/run/docker.sock", target="/var/run/docker.sock", type="bind"),
        docker.types.Mount(source="/sys", target="/sys", type="bind"),
        docker.types.Mount(source=docker_bin, target="/usr/bin/docker", type="bind"),
    ]

    environment = {
        "MESOS_HOSTNAME": bind,
        "MESOS_WD": data,
        "PORT_MASTER": str(port_master if port_master else 5050),
        "PORT_SERVICE": str(port_service if port_service else 8080),
        "ZOOKEEPER": zookeeper
    }
    if not no_agent:
        environment["PORT_AGENT"] = str(port_agent if port_agent else 5051)
    if quorum is not None:
        environment["MESOS_QUORUM"] = str(quorum)
    if name is not None:
        environment["MESOS_CLUSTER"] = name
    if resources is not None:
        environment["MESOS_RESOURCES"] = resources

    if quorum is None:
        image = MESOS_IMAGE_NAME
        command = ["/bin/start-mesos.sh"]
    elif service == "marathon":
        image = MARATHON_IMAGE_NAME
        command = ["/bin/start-marathon.sh"]
        if clear:
            environment["MARATHON_CLEAR"] = "1"
    else:
        image = SINGULARITY_IMAGE_NAME
        command = ["/bin/start-singularity.sh"]
        mounts.append(docker.types.Mount(source=SINGULARITY_LOG, target="/var/log/singularity", type="bind"))
        mounts.append(docker.types.Mount(source=SINGULARITY_CONF, target="/etc/singularity", type="bind"))

        vars = {
            "PORT_SERVICE": environment["PORT_SERVICE"],
            "MESOS_MASTER": environment["MESOS_HOSTNAME"] + ':' + environment["PORT_MASTER"],
            "ZOOKEEPER": zookeeper.replace("zk://", ""),
            "BIND": bind
        }
        if clear:
            utils.rmIfExists(SINGULARITY_LOG)
            utils.rmIfExists(SINGULARITY_CONF)

        utils.mkdirIfNotExists(SINGULARITY_LOG)
        utils.mkdirIfNotExists(SINGULARITY_CONF)

        singularity_res = os.path.join(RESOURCES, "singularity")
        with open(os.path.join(singularity_res, 'config.yaml'), 'r') as f:
            conf = "\n".join(f.readlines())
        for key, value in vars.items():
            conf = conf.replace('${' + key + '}', value)
        with open(os.path.join(SINGULARITY_CONF, 'config.yaml'), 'w') as f:
            f.write(conf)

    container = client.containers.run(
        image=url_namespace + image + img_tag,
        name=CONTAINER_NAME,
        detach=True,
        environment=environment,
        privileged=True,
        command=command,
        mounts=mounts,
        network_mode="host",
        pid_mode="host"
    )


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
