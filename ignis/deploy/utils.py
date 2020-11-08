import base64
import hashlib
import random
import socket
import string
import subprocess


def getHostname():
	try:
		return subprocess.check_output(['hostname', '-s']).decode("utf-8").strip()
	except subprocess.CalledProcessError as ex:
		return socket.gethostname()


def getIpAddress(hostname):
	return socket.gethostbyname(hostname)


def getContainer(client, name):
	containers = client.containers.list(all=True, filters={'name': '^' + name + '$'})
	if len(containers) == 1:
		return containers.pop()


def getStatus(client, name):
	container = getContainer(client, name)
	if not container:
		return 'NOT_FOUND'
	return container.status.upper()


def containerAction(client, name, module, action):
	container = getContainer(client, name)
	if container:
		try:
			action(container)
		except Exception as ex:
			print("error:  " + str(ex))
			exit(-1)
	else:
		print("error: " + module + " not found")
		exit(-1)

def randomPassword():
	return ''.join(random.choices(string.ascii_letters + string.digits, k=10))


def encode(s):
	return s.encode('utf-8')


def decode(bs):
	return bs.decode('utf-8')


def sha1base64(s):
	return base64.b64encode(hashlib.sha1(encode(s)).digest())
