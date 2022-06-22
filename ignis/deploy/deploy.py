#!/usr/bin/env python3

import argparse
import os
import sys

import ignis.deploy.images as images
import ignis.deploy.mesos as mesos
import ignis.deploy.nomad as nomad
import ignis.deploy.registry as registry
import ignis.deploy.registry_ui as registry_ui
import ignis.deploy.submitter as submitter
import ignis.deploy.zookeeper as zookeeper
import ignis.deploy.version as version


def cli():
    # Interface
    parser = argparse.ArgumentParser(prog="ignis-deploy", description='Script for the deploy of an Ignis cluster')
    subparsers = parser.add_subparsers(dest='service', help="Available services")

    # Common
    def common_arguments(parser, force=False, clear=False, registry=False, namespace=False, tag=False):
        if force:
            parser.add_argument('-f', '--force', dest='force', action='store_true',
                                help='Destroy container if exists')
        if clear:
            parser.add_argument('-c', '--clear', dest='clear', action='store_true',
                                help='Clear all previous data')
        if registry:
            parser.add_argument('--docker-registry', dest='registry', action='store', metavar='url',
                                help='Docker image registry', default=None)
        if namespace:
            parser.add_argument('--docker-namespace', dest='namespace', action='store', metavar='name',
                                help='Docker image namespace', default="ignishpc")
        if tag:
            parser.add_argument('--docker-tag', dest='tag', action='store', metavar='tag',
                                help='Docker image tag', default="")

    subparsers.add_parser("version", description='Show version and exits')
    subparsers.add_parser("status", description='Check modules status')
    # Registry
    parser_rty = subparsers.add_parser(registry.MODULE_NAME, description='Image registry')
    subparsers_rty = parser_rty.add_subparsers(dest='action', help="Registry service actions")

    rty_start = subparsers_rty.add_parser("start", description='Start a registry service')
    rty_start.add_argument('-b', '--bind', dest='bind', action='store', metavar='address',
                           help='The address that should be bound to for internal cluster communications, '
                                'default the first available private IPv4 address')
    rty_start.add_argument('-d', '--default', dest='default', action='store_true',
                           help='Set the Image registry as default')
    rty_start.add_argument('--port', dest='port', action='store', metavar='int', type=int,
                           help='Registry server Port, default 5000')
    rty_start.add_argument('--path', dest='path', action='store', metavar='str',
                           help='File System path to store the registry contents, default /var/lib/ignis/registry')
    common_arguments(rty_start, force=True, clear=True)

    rty_garbage = subparsers_rty.add_parser("garbage", description='Run registry garbage collection')
    rty_stop = subparsers_rty.add_parser("stop", description='Stop the registry service')
    rty_resume = subparsers_rty.add_parser("resume", description='Resume the registry service')
    rty_destroy = subparsers_rty.add_parser("destroy", description='Destroy the registry service')

    # Registry-ui
    parser_rty_ui = subparsers.add_parser(registry_ui.MODULE_NAME, description='Image registry-ui')
    subparsers_rty_ui = parser_rty_ui.add_subparsers(dest='action', help="Registry-ui service actions")

    rty_ui_start = subparsers_rty_ui.add_parser("start", description='Start a registry-ui service')
    rty_ui_start.add_argument('--port', dest='port', action='store', metavar='int', type=int,
                              help='Registry-ui server Port, default 3000')
    common_arguments(rty_ui_start, clear=True, force=True)

    rty_ui_stop = subparsers_rty_ui.add_parser("stop", description='Stop the registry-ui service')
    rty_ui_resume = subparsers_rty_ui.add_parser("resume", description='Resume the registry-ui service')
    rty_ui_destroy = subparsers_rty_ui.add_parser("destroy", description='Destroy the registry-ui service')

    # Nomad parser
    parser_nomad = subparsers.add_parser(nomad.MODULE_NAME, description='Nomad cluster')
    subparsers_nomad = parser_nomad.add_subparsers(dest='action', help="Nomad service actions")

    nomad_start = subparsers_nomad.add_parser("start", description='Start a Nomad service')
    nomad_start.add_argument('-b', '--bind', dest='bind', action='store', metavar='address',
                             help='The address that should be bound to for internal cluster communications, '
                                  'default the first available private IPv4 address')
    nomad_start.add_argument('--join', dest='partner', action='store', metavar='address',
                             help='Join to a existing nomad cluster')
    nomad_start.add_argument('-p', '--ports', dest='ports', nargs=3, metavar='int', type=int,
                             help='Ports used by (http, rpc, Serf), default 4646 4647 4648')
    nomad_start.add_argument('--password', dest='password', action='store', metavar='str',
                             help='Password to generate a gossip encryption key, default random')
    nomad_start.add_argument('--config', dest='config', action='store', metavar='file',
                             help='Load a custom json config file')
    nomad_start.add_argument('--name', dest='name', action='store', metavar='str',
                             help='Nomad node name (default bind hostname)')
    nomad_start.add_argument('--data', dest='data', action='store', metavar='path',
                             help='Data directory, default /var/lib/ignis/nomad')
    nomad_start.add_argument('--no-client', dest='no_client', action='store_true',
                             help='Client will not be launched ')
    nomad_start.add_argument('--no-server', dest='no_server', action='store_true',
                             help='Serve will not be launched ')
    nomad_start.add_argument('--docker', dest='docker_bin', action='store', metavar='path',
                             help='Docker binary, default /usr/bin/docker')
    nomad_start.add_argument('--volumes', dest='volumes', metavar='path',
                             nargs="*", help='Allow mount host path as volume', default=[])
    common_arguments(nomad_start, force=True, clear=True, registry=True, namespace=True, tag=True)

    nomad_stop = subparsers_nomad.add_parser("stop", description='Stop the Nomad service')
    nomad_resume = subparsers_nomad.add_parser("resume", description='Resume the Nomad service')
    nomad_destroy = subparsers_nomad.add_parser("destroy", description='Destroy the Nomad service')

    # Zookeper parser
    parser_zk = subparsers.add_parser(zookeeper.MODULE_NAME, description='Zookeeper cluster')
    subparsers_zk = parser_zk.add_subparsers(dest='action', help="Zookeeper service actions")

    zk_start = subparsers_zk.add_parser("start", description='Start a Zookeeper service')
    zk_start.add_argument('-b', '--bind', dest='bind', action='store', metavar='address',
                          help='The address that should be bound to for internal cluster communications, '
                               'default the first available private IPv4 address')
    zk_start.add_argument('-id', dest='id', action='store', metavar='[0-255]',
                          help='Zookeeper server id, by default the field four of ipv4 address is used')
    zk_start.add_argument('--partner', dest='partner', action='store', metavar='address',
                          help='Join to a existing zookeeper cluster')
    zk_start.add_argument('--partnerall', dest='partner', nargs=5, metavar=('address', 'id', 'port', 'port', 'port'),
                          help='Join to a existing zookeeper cluster with a custom configuration')
    zk_start.add_argument('--password', dest='password', action='store', metavar='str',
                          help='Zookeeper super-user password for add new nodes, default random')
    zk_start.add_argument('--logs', dest='logs', action='store', metavar='path',
                          help='Log directory, default /log/ignis/zookeeper')
    zk_start.add_argument('--data', dest='data', action='store', metavar='path',
                          help='Data directory, default /var/lib/ignis/zookeeper')
    zk_start.add_argument('--conf', dest='conf', action='store', metavar='path',
                          help='Conf directory, default /etc/ignis/zookeeper')
    zk_start.add_argument('-p', '--ports', dest='ports', nargs=3, metavar='int', type=int,
                          help='Ports used by zookeper services, default 2888 3888 2181')
    common_arguments(zk_start, force=True, clear=True, registry=True, namespace=True, tag=True)

    zk_stop = subparsers_zk.add_parser("stop", description='Stop the Zookeeper service')
    zk_resume = subparsers_zk.add_parser("resume", description='Resume the Zookeeper service')
    zk_destroy = subparsers_zk.add_parser("destroy", description='Destroy the Zookeeper service')

    # Mesos parser
    parser_mesos = subparsers.add_parser(mesos.MODULE_NAME, description='Mesos cluster')
    subparsers_mesos = parser_mesos.add_subparsers(dest='action', help="Mesos service actions")

    mesos_start = subparsers_mesos.add_parser("start", description='Start a Mesos service')
    mesos_start.add_argument('-s', '--service', dest='mesos_service', action='store',
                             choices=["marathon", "singularity"],
                             default="marathon",
                             help='Choose the service to run on mesos, default marathon')
    mesos_start.add_argument('-b', '--bind', dest='bind', action='store', metavar='address',
                             help='The address that should be bound to for internal cluster communications, '
                                  'default the first available private IPv4 address')
    mesos_start.add_argument('-q', '--master-quorum', dest='quorum', action='store', metavar='int', type=int,
                             help='Set the master mesos quorum, if not specified no master will be created, only slave')
    mesos_start.add_argument('--name', dest='name', action='store', metavar='str',
                             help='Mesos service master name')
    mesos_start.add_argument('-zk', '--zookeeper', dest='zookeeper', action='store', metavar='str',
                             help='Zookeeper Address, default zk://${bind}:2181')
    mesos_start.add_argument('--resources', dest='resources', action='store', metavar='str',
                             help='Mesos resource file, file:/// or string')
    mesos_start.add_argument('--port-master', dest='port_master', action='store', metavar='int', type=int,
                             help='Mesos master Port, default 5050')
    mesos_start.add_argument('--port-agent', dest='port_agent', action='store', metavar='int', type=int,
                             help='Mesos agent Port, default 5051')
    mesos_start.add_argument('--port-service', dest='port_service', action='store', metavar='int', type=int,
                             help='Service Port, default 8080')
    mesos_start.add_argument('--no-agent', dest='no_agent', action='store_true',
                             help='Agent will not be launched ')
    mesos_start.add_argument('--data', dest='data', action='store', metavar='path',
                             help='Data directory, default /var/lib/ignis/mesos')
    mesos_start.add_argument('--docker', dest='docker_bin', action='store', metavar='path',
                             help='Docker binary, default /usr/bin/docker')
    common_arguments(mesos_start, force=True, clear=True, registry=True, namespace=True, tag=True)

    mesos_stop = subparsers_mesos.add_parser("stop", description='Stop the Mesos service')
    mesos_resume = subparsers_mesos.add_parser("resume", description='Resume the Mesos service')
    mesos_destroy = subparsers_mesos.add_parser("destroy", description='Destroy the Mesos service')

    # Submitter parser
    parser_submitter = subparsers.add_parser(submitter.MODULE_NAME, description='Ignis applications submitter')
    subparsers_submitter = parser_submitter.add_subparsers(dest='action', help="Ignis submitter service actions")

    submitter_start = subparsers_submitter.add_parser("start", description='Start a Ignis submitter service')
    submitter_start.add_argument('--dfs', dest='dfs', action='store', metavar='str',
                                 help='Distributed File System path on host machine (required)', required=True)
    submitter_start.add_argument('--dfs-home', dest='dfs_home', action='store', metavar='str',
                                 help='Distributed File System path on containers')
    submitter_start.add_argument('--scheduler', dest='scheduler', action='store', metavar=('name', 'url'), nargs=2,
                                 help='Scheduler used for container allocation (required)', required=True)
    submitter_start.add_argument('--password', dest='password', action='store', metavar='str',
                                 help='Set the root password, default ignis')
    submitter_start.add_argument('--host-dns', dest='dns', action='store_true',
                                 help='Enable host dns names')
    submitter_start.add_argument('--port', dest='port', action='store', metavar='int', type=int,
                                 help='SSH server Port, default 2222')
    submitter_start.add_argument('--env', dest='envs', action='append', metavar=('key', 'value'),
                                 nargs="+", help='Create environment variable inside submit', default=[])
    submitter_start.add_argument('--mount', dest='mounts', action='append', metavar=('host', 'container'), nargs="+"
                                 , help='Create environment variable inside submit. Use <host>:ro to read only',
                                 default=[])
    common_arguments(submitter_start, force=True, clear=False, registry=True, namespace=True, tag=True)

    submitter_stop = subparsers_submitter.add_parser("stop", description='Stop the Ignis submitter service')
    submitter_resume = subparsers_submitter.add_parser("resume", description='Resume the Ignis submitter service')
    submitter_destroy = subparsers_submitter.add_parser("destroy", description='Destroy the Ignis submitter service')

    # Images
    parser_submitter = subparsers.add_parser(images.MODULE_NAME, description='Ignis images manager')
    subparsers_images = parser_submitter.add_subparsers(dest='action', help="Ignis images actions")

    images_clear = subparsers_images.add_parser("clear", description='Delete all Ignis images')
    images_clear.add_argument('-y', dest='yes', action='store_true', default=False,
                              help='Assume yes in clear confirmation')
    images_clear.add_argument('--version', dest='version', action='store', metavar='str',
                              help='Delete only a selected version')
    images_clear.add_argument('--whitelist', dest='whitelist', metavar='image',
                              nargs="*", help='Only clears images in the white list', default=None)
    images_clear.add_argument('--blacklist', dest='blacklist', metavar='image',
                              nargs="+", help='Ignore images(including whitelist) in the black list', default=[])

    class NegateAction(argparse.Action):
        def __call__(self, parser, ns, values, option):
            setattr(ns, self.dest, option[0:5] != '--no-')

    images_clear.add_argument('--none', '--no-none', dest='add_none', action=NegateAction, nargs=0, default=False,
                              help='Add or ignore images with <none> tag, default(--no-none)')
    images_clear.add_argument('-f', '--force', dest='force', action='store_true',
                              help='Force image deletion')
    common_arguments(images_clear, registry=True, namespace=True)

    images_push = subparsers_images.add_parser("push", description='Push all Ignis images')
    images_push.add_argument('-y', dest='yes', action='store_true', default=False,
                             help='Assume yes in push confirmation')
    images_push.add_argument('--builders', dest='builders', action='store_true', default=False,
                             help='Push builders to the repository, default false')
    images_push.add_argument('--version', dest='version', action='store', metavar='str',
                             help='Push only a selected version')
    images_push.add_argument('--whitelist', dest='whitelist', metavar='image',
                             nargs="+", help='Only pushes images in the white list', default=None)
    images_push.add_argument('--blacklist', dest='blacklist', metavar='image',
                             nargs="+", help='Ignore images(including whitelist) in the black list', default=[])
    common_arguments(images_push, registry=True, namespace=True)

    images_build = subparsers_images.add_parser("build", description='Build Ignis images')
    images_build.add_argument('--sources', dest='sources', action='store', metavar='url', nargs="*",
                              help='URL core repositories(git)', default=[])
    images_build.add_argument('--local-sources', dest='local_sources', action='store', metavar='path', nargs="*",
                              help='Path core folders', default=[])
    images_build.add_argument('--ignore', dest='ignore_folders', action='store', metavar='folder', nargs="*",
                              help='Ignore folders in list', default=[])
    images_build.add_argument('--version-filter', dest='version_filters', action='append', metavar=('name', 'version'),
                              nargs=2, help='Path core folders', default=[])
    images_build.add_argument('--full', dest='full', action='store_true',
                              help='Create a full image with all cores', default=False)
    images_build.add_argument('--bases', dest='bases', action='store_true',
                              help='Create common base images with driver and executor installed', default=False)
    images_build.add_argument('--logs', dest='logs', action='store_true',
                              help='Always create log', default=False)
    images_build.add_argument('--version', dest='version', action='store', metavar='str',
                              help='Default build version')
    images_build.add_argument('--version-tags', dest='version_tags', metavar="str",
                              nargs="*", help='Additional version tags', default=[])
    images_build.add_argument('--custom-image', dest='custom_images', action='append', metavar=('name', 'cores'),
                              nargs="+", help='Path core folders', default=[])
    images_build.add_argument('--platform', dest='platform', action='store',
                              help='Create ignis images for one or more platforms, requires buildx.')
    common_arguments(images_build, registry=True, namespace=True)

    images_singularity = subparsers_images.add_parser("singularity",
                                                      description='Create a Singularity image from docker')
    images_singularity.add_argument('image', help='Docker image to convert to singularity.')
    images_singularity.add_argument('output', action='store', help='Singularity image file output.')
    images_singularity.add_argument('--host', dest='host', action='store_true',
                              help='Use local singularity instead of docker container', default=False)
    images_singularity.add_argument('--platform', dest='platform', action='store',
                              help='Create a singularity images using other platform, requires buildx.')
    common_arguments(images_singularity, registry=True, force=True)

    args = parser.parse_args(['-h'] if len(sys.argv) == 1 else None)
    if args.service == "version":
        print(version.__version__)
        exit(0)

    if "action" in args and not args.action:
        subparsers.choices[args.service].print_help()
        sys.exit(0)

    default_registry = registry.parse(args.registry if "registry" in args else None)
    namespace = args.namespace if "namespace" in args else ""
    img_tag = args.tag if "tag" in args else ""
    if len(namespace) > 0 and namespace[-1] != "/":
        namespace += "/"
    if len(img_tag) > 0 and img_tag[0] != ':':
        img_tag = ":" + img_tag
    url_namespace = default_registry + namespace

    if args.service == "status":
        print("Service Status:")
        print("    Registry  " + registry.status())
        print(" Registry-ui  " + registry_ui.status())
        print("       Nomad  " + nomad.status())
        print("   Zookeeper  " + zookeeper.status())
        print("       Mesos  " + mesos.status())
        print("   Submitter  " + submitter.status())
    elif args.service == registry.MODULE_NAME:
        if args.action == "start":
            registry.start(bind=args.bind,
                           port=args.port,
                           path=args.path,
                           default=args.default,
                           clear=args.clear,
                           force=args.force)
        elif args.action == "garbage":
            registry.garbage()
        elif args.action == "stop":
            registry.stop()
        elif args.action == "resume":
            registry.resume()
        elif args.action == "destroy":
            registry.destroy()
    elif args.service == registry_ui.MODULE_NAME:
        if args.action == "start":
            registry_ui.start(port=args.port,
                              registry=default_registry,
                              force=args.force)
        elif args.action == "stop":
            registry.stop()
        elif args.action == "resume":
            registry.resume()
        elif args.action == "destroy":
            registry.destroy()
    elif args.service == nomad.MODULE_NAME:
        if args.action == "start":
            nomad.start(bind=args.bind,
                        partner=args.partner,
                        ports=args.ports,
                        password=args.password,
                        config_file=args.config,
                        name=args.name,
                        data=args.data,
                        no_client=args.no_client,
                        no_server=args.no_server,
                        docker_bin=args.docker_bin,
                        volumes=args.volumes,
                        url_namespace=url_namespace,
                        img_tag=img_tag,
                        force=args.force,
                        clear=args.clear)
        elif args.action == "stop":
            nomad.stop()
        elif args.action == "resume":
            nomad.resume()
        elif args.action == "destroy":
            nomad.destroy()
    elif args.service == zookeeper.MODULE_NAME:
        if args.action == "start":
            zookeeper.start(bind=args.bind,
                            id=args.id,
                            partner=args.partner,
                            password=args.password,
                            ports=args.ports,
                            logs=args.logs,
                            conf=args.conf,
                            data=args.data,
                            url_namespace=url_namespace,
                            img_tag=img_tag,
                            clear=args.clear,
                            force=args.force)
        elif args.action == "stop":
            zookeeper.stop()
        elif args.action == "resume":
            zookeeper.resume()
        elif args.action == "destroy":
            zookeeper.destroy()
    elif args.service == mesos.MODULE_NAME:
        if args.action == "start":
            mesos.start(service=args.mesos_service,
                        bind=args.bind,
                        quorum=args.quorum,
                        name=args.name,
                        zookeeper=args.zookeeper,
                        resources=args.resources,
                        port_master=args.port_master,
                        port_agent=args.port_agent,
                        port_service=args.port_service,
                        no_agent=args.no_agent,
                        data=args.data,
                        docker_bin=args.docker_bin,
                        url_namespace=url_namespace,
                        img_tag=img_tag,
                        clear=args.clear,
                        force=args.force,
                        )
        elif args.action == "stop":
            mesos.stop()
        elif args.action == "resume":
            mesos.resume()
        elif args.action == "destroy":
            mesos.destroy()
    elif args.service == submitter.MODULE_NAME:
        if args.action == "start":
            submitter.start(port=args.port,
                            dfs=args.dfs,
                            dfs_home=args.dfs_home,
                            password=args.password,
                            scheduler=args.scheduler[0],
                            shceduler_url=args.scheduler[1],
                            dns=args.dns,
                            envs=args.envs,
                            mounts=args.mounts,
                            default_registry=default_registry,
                            url_namespace=url_namespace,
                            img_tag=img_tag,
                            force=args.force)
        elif args.action == "stop":
            submitter.stop()
        elif args.action == "resume":
            submitter.resume()
        elif args.action == "destroy":
            submitter.destroy()
    elif args.service == images.MODULE_NAME:
        if args.action == "clear":
            images.clear(yes=args.yes,
                         version=args.version,
                         whitelist=args.whitelist,
                         blacklist=args.blacklist,
                         add_none=args.add_none,
                         force=args.force,
                         default_registry=default_registry,
                         namespace=namespace)
        elif args.action == "push":
            images.push(yes=args.yes,
                        builders=args.builders,
                        version=args.version,
                        whitelist=args.whitelist,
                        blacklist=args.blacklist,
                        default_registry=default_registry,
                        namespace=namespace)
        elif args.action == "build":
            images.build(sources=args.sources,
                         local_sources=args.local_sources,
                         ignore_folders=args.ignore_folders,
                         version_filters=args.version_filters,
                         custom_images=args.custom_images,
                         bases=args.bases,
                         full=args.full,
                         save_logs=args.logs,
                         version_tags=args.version_tags,
                         version=args.version,
                         default_registry=default_registry,
                         namespace=namespace,
                         platform=args.platform)
        elif args.action == "singularity":
            images.singularity(name=args.image,
                               output=args.output,
                               host=args.host,
                               default_registry=default_registry,
                               platform=args.platform,
                               force=args.force)


def main():
    try:
        cli()
    except KeyboardInterrupt as ex:
        print("\nAborted")
        exit(-1)
    except PermissionError:
        print("root required!!", file=sys.stderr)
        sys.exit(-1)
    except Exception as ex:
        print(str(type(ex).__name__) + ":  " + str(ex), file=sys.stderr)
        if "IGNIS_DEBUG" in os.environ and os.environ["IGNIS_DEBUG"]:
            raise ex
        exit(-1)


if __name__ == "__main__":
    main()
