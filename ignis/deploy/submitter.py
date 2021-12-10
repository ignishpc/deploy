import os

import docker

import ignis.deploy.utils as utils

IMAGE_NAME = "submitter"
MODULE_NAME = "submitter"
CONTAINER_NAME = "ignis-submitter"


def start(port, dfs, dfs_home, password, scheduler, shceduler_url, dns, envs, mounts, default_registry, url_namespace,
          img_tag, force):
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

    mounts_list = [
        docker.types.Mount(source=dfs, target=dfs_home, type="bind"),
    ]

    for mount in mounts:
        source = mount[0].split(":")[0]
        ro = source[0].endswith(":ro")
        mounts_list.append(docker.types.Mount(source=source, target=mount[1], type="bind", read_only=ro))

    environment = {
        "IGNIS_DFS_ID": dfs,
        "IGNIS_DFS_HOME": dfs_home,
        "IGNIS_SCHEDULER_TYPE": scheduler,
        "IGNIS_SCHEDULER_URL": shceduler_url,
    }

    for env in envs:
        environment[env[0]] = env[1]

    tz = _timezone()
    if tz is not None:
        environment["TZ"] = tz

    extra_hosts = dict()
    if dns:
        import python_hosts
        hosts = python_hosts.Hosts()
        dns = list()
        for host in hosts.entries:
            if host.entry_type == 'ipv4':
                for name in host.names:
                    dns.append(name + ':' + host.address)
                    extra_hosts[name] = host.address

        environment["IGNIS_SCHEDULER_DNS"] = ','.join(dns)

    if default_registry:
        environment["IGNIS_REGISTRY"] = default_registry

    container_ports = {
        "22": str(port)
    }

    command = ["/opt/ignis/bin/ignis-sshd"]

    container = client.containers.run(
        image=url_namespace + IMAGE_NAME + img_tag,
        name=CONTAINER_NAME,
        detach=True,
        environment=environment,
        command=command,
        mounts=mounts_list,
        ports=container_ports,
        extra_hosts=extra_hosts
    )

    container.exec_run(["bash", "-c", 'echo "root:' + password + '" | chpasswd'])


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


def _timezone():
    if "TZ" in os.environ:
        return os.getenv("TZ")

    if os.path.exists("/etc/timezone"):
        with open("/etc/timezone") as file:
            return file.readline().rstrip()

    try:
        from tzlocal import get_localzone
        return get_localzone().zone
    except Exception:
        pass

    try:
        from subprocess import run, PIPE
        timeinfo = run(["timedatectl", "status"], stdout=PIPE).stdout.decode("utf-8")
        key = "Time zone:"
        i = timeinfo.index(key) + len(key) + 1
        j = timeinfo.index(" ", i)
        return timeinfo[i:j]
    except Exception:
        pass

    return None
