#!/usr/bin/env python3

import argparse
import sys
import zookeeper
import mesos
import submitter
import glusterfs


def cli():
	# Interface
	parser = argparse.ArgumentParser(prog="ignis-deploy", description='Script for the deploy of an Ignis cluster')
	subparsers = parser.add_subparsers(dest='service', help="Available services")

	parser_check = subparsers.add_parser("status", description='Check modules status')
	# Zookeper parser
	parser_zk = subparsers.add_parser("zookeeper", description='Manages a Zookeeper cluster')
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
	                      help='Ports used by allocator services, default 2888 3888 2181')
	zk_start.add_argument('-f', '--force', dest='force', action='store_true',
	                      help='Destroy the allocator if exists')

	parser_zk_stop = subparsers_zk.add_parser("stop", description='Stop the Zookeeper service')
	parser_zk_resume = subparsers_zk.add_parser("resume", description='Resume the Zookeeper service')
	parser_zk_destroy = subparsers_zk.add_parser("destroy", description='Destroy the Zookeeper service')

	# Mesos parser
	parser_mesos = subparsers.add_parser("mesos", description='Start a Mesos service')
	subparsers_mesos = parser_mesos.add_subparsers(dest='action', help="Mesos service actions")

	mesos_start = subparsers_mesos.add_parser("start", description='Start a Zookeeper service')
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
	                         help='Marathon web Port, default 8080')
	mesos_start.add_argument('--data', dest='data', action='store', metavar='path',
	                         help='Data directory, default /var/lib/ignis/mesos')
	mesos_start.add_argument('--docker', dest='docker_bin', action='store', metavar='path',
	                         help='Docker binary, default /usr/local/bin/docker')
	mesos_start.add_argument('-f', '--force', dest='force', action='store_true',
	                         help='Destroy the allocator if exists')

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
	parser_submitter = subparsers.add_parser("submitter", description='Manages the Ignis applications submitter')
	subparsers_submitter = parser_submitter.add_subparsers(dest='action', help="Ignis submitter service actions")

	submitter_start = subparsers_submitter.add_parser("start", description='Start a Ignis submitter service')

	submitter_stop = subparsers_submitter.add_parser("stop", description='Stop the Ignis submitter service')
	submitter_resume = subparsers_submitter.add_parser("resume", description='Resume the Ignis submitter service')
	submitter_destroy = subparsers_submitter.add_parser("destroy", description='Destroy the Ignis submitter service')


	args = parser.parse_args(['-h'] if len(sys.argv) == 1 else None)

	if "action" in args and not args.action:
		subparsers.choices[args.service].print_help()
		sys.exit(0)

	if args.service == "status":
		print("Service Status:")
		print("  Zookeeper  " + zookeeper.status())
		print("      Mesos  " + mesos.status())
		print("  Submitter  " + submitter.status())
		print("  GlusterFS  " + glusterfs.status())
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
			submitter.start()
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
