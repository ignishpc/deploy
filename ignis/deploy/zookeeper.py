import os
import shutil
import sys
import time

import docker

import ignis.deploy.utils as utils

IMAGE_NAME = "zookeeper"
MODULE_NAME = "zookeeper"
CONTAINER_NAME = "ignis-zookeeper"
CONTAINER_LOG = "/var/log/ignis/zookeeper/"
CONTAINER_CONF = "/etc/ignis/zookeeper/"
CONTAINER_DATA = "/var/lib/ignis/zookeeper/"
RESOURCES = os.path.join(os.path.dirname(os.path.realpath(__file__)), "resources")


def start(bind, id, partner, password, ports, logs, conf, data, url_namespace, img_tag, clear, force):
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

    bind = utils.getIpAddress(bind)
    if bind is None:
        print("error:  hostname '" + bind + "' not found")
        exit(-1)

    if id is None:
        id = bind.split('.')[3]

    if password is None:
        password = utils.randomPassword()

    zk_token = "super:" + utils.sha1base64("super:" + password)

    if ports is None:
        ports = [
            2888,
            3888,
            2181,
        ]
    container_ports = dict()
    for port in ports:
        container_ports[str(port)] = str(port)

    my_server = "server." + id + "=" + bind + ":" + str(ports[0]) + ":" + str(ports[1]) + ";" + str(ports[2])

    if type(partner) == str:
        partner_ip = utils.getIpAddress(partner)
        if not partner_ip:
            print("error:  hostname '" + partner + "' not found")
            exit(-1)
        partner_id = partner_ip.split('.')[3]
        partner_server = "server." + partner_id + "=" + partner + ":" + str(ports[0]) + ":" + str(ports[1]) + ";" + \
                         str(ports[2])
    elif type(partner) == list:
        partner_ip = utils.getIpAddress(partner[1])
        if not partner_ip:
            print("error:  hostname '" + partner[1] + "' not found")
            exit(-1)
        partner_server = "server." + partner[0] + "=" + partner_ip + ":" + partner[2] + ":" + partner[3] + ";" + \
                         partner[4]

    if logs is None:
        logs = CONTAINER_LOG

    if conf is None:
        conf = CONTAINER_CONF

    if data is None:
        data = CONTAINER_DATA

    if clear:
        utils.rmIfExists(logs)
        utils.rmIfExists(conf)
        utils.rmIfExists(data)

    utils.mkdirIfNotExists(logs)
    utils.mkdirIfNotExists(conf)
    utils.mkdirIfNotExists(data)

    zookeeper_res = os.path.join(RESOURCES, "zookeeper")
    with open(os.path.join(zookeeper_res, 'myid'), 'w') as f:
        f.write(str(id))
    with open(os.path.join(zookeeper_res, 'zoo.cfg.dynamic'), 'w') as f:
        f.write(my_server + "\n")
        if partner:
            f.write(partner_server)
    for filename in os.listdir(zookeeper_res):
        shutil.copy(os.path.join(zookeeper_res, filename), conf)
    shutil.move(os.path.join(conf, 'myid'), os.path.join(os.path.abspath(data),'myid'))

    mounts = [
        docker.types.Mount(source=logs, target="/var/log/zookeeper/", type="bind"),
        docker.types.Mount(source=conf, target="/etc/zookeeper/conf/", type="bind"),
        docker.types.Mount(source=data, target="/var/lib/zookeeper/data/", type="bind"),
    ]

    environment = {
        "JVMFLAGS": "-Djava.security.auth.login.config=/etc/zookeeper/conf/jaas.conf  "
                    "-Dzookeeper.DigestAuthenticationProvider.superDigest=" + zk_token,
    }

    command = ["/opt/zookeeper/bin/zkServer.sh", "start-foreground"]

    container = client.containers.run(
        image=url_namespace + IMAGE_NAME + img_tag,
        name=CONTAINER_NAME,
        detach=True,
        environment=environment,
        privileged=True,
        command=command,
        mounts=mounts,
        ports=container_ports
    )

    if partner is not None:
        partner_check = False
        for i in range(1, 11):
            time.sleep(i % 5)
            _, pipe = container.exec_run(["/opt/ignis/bin/auth-cli.sh"], socket=True, stdin=True)
            pipe._sock.sendall(utils.encode(str(ports[2]) + "\n"))
            pipe._sock.sendall(utils.encode("addauth digest super:" + password + "\n"))
            pipe._sock.sendall(utils.encode("reconfig -add " + my_server + "\n"))
            out = pipe.readlines()
            if "Committed new configuration" in str(out):
                partner_check = True
                break
        if not partner_check:
            print("error: failed to join to the partner " + str(out))
            destroy()


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
