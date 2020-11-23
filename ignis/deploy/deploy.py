#!/usr/bin/env python3

import argparse
import sys

import glusterfs
import mesos
import registry
import submitter
import zookeeper


def cli():
	# Interface
	parser = argparse.ArgumentParser(prog="ignis-deploy", description='Script for the deploy of an Ignis cluster')
	subparsers = parser.add_subparsers(dest='service', help="Available services")

	parser_check = subparsers.add_parser("status", description='Check modules status')
	# Registry
	parser_rty = subparsers.add_parser("registry", description='Image registry')
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
	rty_start.add_argument('-f', '--force', dest='force', action='store_true',
	                       help='Destroy the image registry if exists')

	rty_stop = subparsers_rty.add_parser("stop", description='Stop the registry service')
	rty_resume = subparsers_rty.add_parser("resume", description='Resume the registry service')
	rty_destroy = subparsers_rty.add_parser("destroy", description='Destroy the registry service')

	# Zookeper parser
	parser_zk = subparsers.add_parser("zookeeper", description='Zookeeper cluster')
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
	zk_start.add_argument('-f', '--force', dest='force', action='store_true',
	                      help='Destroy the zookeper if exists')
	zk_start.add_argument('--default-registry', dest='registry', action='store', metavar='url',
	                      help='Docker image registry to pull image')

	zk_stop = subparsers_zk.add_parser("stop", description='Stop the Zookeeper service')
	zk_resume = subparsers_zk.add_parser("resume", description='Resume the Zookeeper service')
	zk_destroy = subparsers_zk.add_parser("destroy", description='Destroy the Zookeeper service')

	# Mesos parser
	parser_mesos = subparsers.add_parser("mesos", description='Mesos cluster')
	subparsers_mesos = parser_mesos.add_subparsers(dest='action', help="Mesos service actions")

	mesos_start = subparsers_mesos.add_parser("start", description='Start a Mesos service')
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
	mesos_start.add_argument('--port-marathon', dest='port_marathon', action='store', metavar='int', type=int,
	                         help='Marathon http Port, default 8080')
	mesos_start.add_argument('--data', dest='data', action='store', metavar='path',
	                         help='Data directory, default /var/lib/ignis/mesos')
	mesos_start.add_argument('--docker', dest='docker_bin', action='store', metavar='path',
	                         help='Docker binary, default /usr/bin/docker')
	mesos_start.add_argument('-f', '--force', dest='force', action='store_true',
	                         help='Destroy the mesos if exists')
	mesos_start.add_argument('--default-registry', dest='registry', action='store', metavar='url',
	                         help='Docker image registry to pull image')

	mesos_stop = subparsers_mesos.add_parser("stop", description='Stop the Mesos service')
	mesos_resume = subparsers_mesos.add_parser("resume", description='Resume the Mesos service')
	mesos_destroy = subparsers_mesos.add_parser("destroy", description='Destroy the Mesos service')

	# GlusterFS parser
	parser_glusterfs = subparsers.add_parser("glusterfs", description='Distributed file system (DFS) Glusterfs service')
	subparsers_glusterfs = parser_glusterfs.add_subparsers(dest='action', help="Glusterfs service actions")

	glusterfs_start = subparsers_glusterfs.add_parser("start", description='Start a Glusterfs service')

	glusterfs_stop = subparsers_glusterfs.add_parser("stop", description='Stop the Glusterfs service')
	glusterfs_resume = subparsers_glusterfs.add_parser("resume", description='Resume the Glusterfs service')
	glusterfs_destroy = subparsers_glusterfs.add_parser("destroy", description='Destroy the Glusterfs service')

	# Submitter parser
	parser_submitter = subparsers.add_parser("submitter", description='Ignis applications submitter')
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
	submitter_start.add_argument('-f', '--force', dest='force', action='store_true',
	                             help='Destroy the submitter if exists')
	submitter_start.add_argument('--default-registry', dest='registry', action='store', metavar='url',
	                             help='Docker image registry to pull image')

	submitter_stop = subparsers_submitter.add_parser("stop", description='Stop the Ignis submitter service')
	submitter_resume = subparsers_submitter.add_parser("resume", description='Resume the Ignis submitter service')
	submitter_destroy = subparsers_submitter.add_parser("destroy", description='Destroy the Ignis submitter service')

	args = parser.parse_args(['-h'] if len(sys.argv) == 1 else None)

	if "action" in args and not args.action:
		subparsers.choices[args.service].print_help()
		sys.exit(0)

	default_registry = registry.parse(args.registry if "registry" in args else "")

	if args.service == "status":
		print("Service Status:")
		print("   Registry  " + registry.status())
		print("  Zookeeper  " + zookeeper.status())
		print("      Mesos  " + mesos.status())
		print("  Submitter  " + submitter.status())
		print("  GlusterFS  " + glusterfs.status())
	elif args.service == "registry":
		if args.action == "start":
			registry.start(bind=args.bind,
			               port=args.port,
			               path=args.path,
			               default=args.default,
			               force=args.force)
		elif args.action == "stop":
			registry.stop()
		elif args.action == "resume":
			registry.resume()
		elif args.action == "destroy":
			registry.destroy()
	elif args.service == "zookeeper":
		if args.action == "start":
			zookeeper.start(bind=args.bind,
			                id=args.id,
			                partner=args.partner,
			                password=args.password,
			                ports=args.ports,
			                logs=args.logs,
			                conf=args.conf,
			                data=args.data,
			                default_registry=default_registry,
			                force=args.force)
		elif args.action == "stop":
			zookeeper.stop()
		elif args.action == "resume":
			zookeeper.resume()
		elif args.action == "destroy":
			zookeeper.destroy()
	elif args.service == "mesos":
		if args.action == "start":
			mesos.start(bind=args.bind,
			            quorum=args.quorum,
			            name=args.name,
			            zookeeper=args.zookeeper,
			            resources=args.resources,
			            port_master=args.port_master,
			            port_agent=args.port_agent,
			            port_marathon=args.port_marathon,
			            data=args.data,
			            docker_bin=args.docker_bin,
			            default_registry=default_registry,
			            force=args.force,
			            )
		elif args.action == "stop":
			mesos.stop()
		elif args.action == "resume":
			mesos.resume()
		elif args.action == "destroy":
			mesos.destroy()
	elif args.service == "submitter":
		if args.action == "start":
			submitter.start(port=args.port,
			                dfs=args.dfs,
			                dfs_home=args.dfs_home,
			                password=args.password,
			                scheduler=args.scheduler[0],
			                shceduler_url=args.scheduler[1],
			                dns=args.dns,
			                default_registry=default_registry,
			                force=args.force)
		elif args.action == "stop":
			submitter.stop()
		elif args.action == "resume":
			submitter.resume()
		elif args.action == "destroy":
			submitter.destroy()
	elif args.service == "glusterfs":
		if args.action == "start":
			glusterfs.start()
		elif args.action == "stop":
			glusterfs.stop()
		elif args.action == "resume":
			glusterfs.resume()
		elif args.action == "destroy":
			glusterfs.destroy()


if __name__ == "__main__":
	cli()
