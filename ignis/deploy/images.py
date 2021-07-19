import os
import re
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from distutils.version import StrictVersion

import docker
import docker.errors
import git


def clear(yes, version, whitelist, blacklist, add_none, force, default_registry):
	try:
		client = docker.from_env()
		images = __getImages(client, version, default_registry)
		filtered_images = __filter(images, whitelist, blacklist, add_none, default_registry)

		print("Following images will be clear")
		for img in filtered_images:
			print(img.id, "    ", img.attrs['RepoTags'])
		option = yes
		if not option:
			option = input("Are you sure (yes/no): ")
			while option not in ["yes", "no"]:
				option = input("Please type yes/no: ")
		if option == "yes":
			for img in filtered_images:
				client.images.remove(image=img.id, force=force)
		else:
			print("Aborted")
	except Exception as ex:
		print("error:  " + str(ex), file=sys.stderr)
		exit(-1)


def push(version, whitelist, blacklist, default_registry):
	try:
		client = docker.from_env()
		images = __getImages(client, version, default_registry)

		for img in __filter(images, whitelist, blacklist, False, default_registry):
			client.images.push(img.id)

	except Exception as ex:
		print("error:  " + str(ex), file=sys.stderr)
		exit(-1)


def build(sources, local_sources, version_filters, custom_images, bases, full, save_logs, version, default_registry):
	try:
		with tempfile.TemporaryDirectory(prefix="ignis") as wd:
			core_list = list()
			version_map = dict()
			for vf in version_filters:
				version_map[vf[0]] = vf[1]

			tmp = os.path.join(wd, "tmp")

			def prepare_sources(folder, local):
				dockerfiles = os.path.join(folder, "Dockerfiles")
				if not os.path.exists(dockerfiles):
					print("warn: " + folder + " ignored, Dockerfiles folder not found")
					return
				subfolders = os.listdir(dockerfiles)
				for core in subfolders:
					core_folder = os.path.join(wd, core)
					if core == subfolders[-1] and not local:
						os.rename(folder, core_folder)
					else:
						shutil.copytree(folder, core_folder)

					v = __setVersion(core, core_folder, version_map.get(core, version), version is None)
					print("  " + core + ":" + v)
					core_list.append((core_folder, v))

			print("Sources:")
			for src in sources:
				git.Repo.clone_from(src, tmp)
				prepare_sources(tmp, False)

			for src in local_sources:
				prepare_sources(src, True)

			print("Dockerfiles:")
			build_list = list()
			for path, v in core_list:
				folder = os.path.join(path, "Dockerfiles", os.path.basename(path))
				dfiles = __find(folder, "Dockerfile")
				for dfile in dfiles:
					order_file = os.path.join(os.path.dirname(dfile), "order")
					if os.path.exists(order_file):
						with open(order_file) as f:
							order = int(f.readline())
					else:
						order = 100
					id = os.path.relpath(os.path.dirname(dfile), os.path.join(path, "Dockerfiles")).replace("/", "-")
					build_list.append({
						"id": id,
						"name": default_registry + "ignishpc/" + id,
						"path": path,
						"dockerfile": dfile,
						"log": os.path.join(os.path.dirname(dfile), "build.log"),
						"version": v,
						"order": order,
					})
					print("  " + os.path.relpath(build_list[-1]["dockerfile"], build_list[-1]["path"]))

			real_cores = dict()
			print("Cores:")
			for core in build_list[:]:
				if core["id"].endswith("-builder"):
					id = core["id"][0: -len("-builder")]
					real_cores[id] = core
					print("  " + id)
					if core["id"] in ("driver-builder", "executor-builder") or \
							(not bases and core["id"] == "common-builder"):
						continue
					build_list.append(
						__createDockerfile(wd, id + "-driver", ["driver", id], core["version"], default_registry, 200))
					build_list.append(
						__createDockerfile(wd, id + "-executor", ["executor", id], core["version"], default_registry,
						                   200))
					build_list.append(
						__createDockerfile(wd, id if id != "common" else "common-full", ["driver", "executor", id],
						                   core["version"], default_registry, 201))

			if real_cores and full:
				custom_images.insert(0, ["full", "driver", "executor"] + list(real_cores.keys()))

			i = 201
			for img in custom_images:
				i += 1
				if version:
					custom_version = version
				elif "common" in real_cores:
					custom_version = real_cores["common"]["version"]
				else:
					custom_version = "latest"
				build_list.append(__createDockerfile(wd, img[0], img[1:], custom_version, default_registry, i))

			build_list.sort(key=lambda x: x["order"])

			print("Images:")
			order = None
			for build in build_list:
				if build["order"] != order:
					print("  ---(" + str(build["order"]) + ")---")
				order = build["order"]
				print("  " + build["name"] + ":" + build["version"])

			build_list.append({
				"order": None
			})

			print("Build:")
			with ThreadPoolExecutor() as executor:
				wait_list = list()
				order = build_list[0]["order"]
				for build in build_list:
					if build["order"] != order:
						error = None
						for info, wait in wait_list:
							log = os.path.join(os.getcwd(), "ignisbuild-" + info["id"] + ".log")
							try:
								print("  " + info["name"] + ":" + info["version"], end=" ", flush=True)
								wait.result()
								print("SUCCESS")
								if save_logs:
									shutil.copy(info["log"], log)
							except Exception as ex:
								print("FAILED, check " + log)
								shutil.copy(info["log"], log)
								error = ex
						if error:
							print("Aborting")
							raise error
						wait_list.clear()
					order = build["order"]
					if order is None:
						break
					wait_list.append((build, executor.submit(
						__docker_build,
						name=build["name"],
						path=build["path"],
						dockerfile=build["dockerfile"],
						log=build["log"],
						version=build["version"],
						default_registry=default_registry
					)))
			print("Build end")
	except Exception as ex:
		print("error:  " + str(ex), file=sys.stderr)
		exit(-1)


def __filter(images, whitelist, blacklist, add_none, default_registry):
	tags = dict()
	tags_none = list()
	prefix = "ignishpc/"
	for img in images:
		tag_list = img.attrs['RepoTags']
		if len(tag_list) == 0 and add_none:
			tags_none.append(img)
		for tag in tag_list:
			if tag.startswith(default_registry):
				name = tag[0:len(default_registry)].split(':')[0]
				if name.startswith(prefix):
					name = name[0:len(prefix)]
					tags[name] = img

	if whitelist:
		tags2 = dict()
		for img in whitelist:
			if img in tags:
				tags2[img] = tags[tags]
		tags = tags2

	for img in blacklist:
		del tags[img]

	return list(set(list(tags.values()) + tags_none))


def __getImages(client, version, default_registry):
	if version is None:
		return client.images.list(name=default_registry, filters={"label": ["ignis"]})
	else:
		return client.images.list(name=default_registry, filters={"label": ["ignis=" + version]})


def __is_git(path):
	try:
		_ = git.Repo(path).git_dir
		return True
	except git.exc.InvalidGitRepositoryError:
		return False


def __find(path, name):
	result = []
	for root, dirs, files in os.walk(path):
		if name in files:
			result.append(os.path.join(root, name))
	return result


def __setVersion(name, path, version, strict):
	if version is None:
		return "latest"
	if __is_git(path) and not strict:
		print("warn: " + name + " version " + version + " ignored because is not a git repository")
		return version
	repo = git.Repo(path)
	tags = sorted(repo.tags, key=StrictVersion)
	found = False
	for tag in tags:
		if tag.startswith(version):
			found = True
			break
	if not found:
		raise ValueError("error: " + name + " has not version " + version)
	repo.heads[tag].checkout()
	return tag


def __docker_build(name, path, dockerfile, log, version, default_registry):
	error = None
	try:
		client = docker.from_env()
		imageObj, buildlog = client.images.build(
			path=path,
			dockerfile=dockerfile,
			labels={
				"ignis": version
			},
			tag=name + ":" + version,
			buildargs={
				"REGISTRY": default_registry,
				"TAG": ":" + version,
				"RELPATH": os.path.relpath(os.path.dirname(dockerfile), path) + "/"
			}
		)
	except docker.errors.BuildError as ex:
		buildlog = ex.build_log
		manifest_error = re.compile(".*manifest for (.*) not found.*")
		result = manifest_error.search(ex.msg)
		if result:
			error = RuntimeError(result.group(1) + " required, use --sources or --local-source to add Dockerfile")
	except Exception as ex:
		buildlog = []
		error = ex

	# Remove ANSI color codes from the string.
	strip = re.compile('\033\\[([0-9]+)(;[0-9]+)*m')
	with open(log, "w") as file:
		for raw in buildlog:
			if 'stream' in raw:
				file.write(re.sub(strip, '', raw['stream']))
	if error:
		raise error

	return imageObj


def __createDockerfile(wd, id, cores, version, default_registry, order=100):
	cores = list(sorted(set(cores)))
	driver = False
	executor = False
	if "common" in cores:
		cores.remove("common")
	if "executor" in cores:
		executor = True
		cores.remove("executor")
	if "driver" in cores:
		driver = True
		cores.remove("driver")

	path = os.path.join(wd, id + "-Dockerfile")
	os.mkdir(path)
	dfile = os.path.join(wd, os.path.join(path, "Dockerfile"))
	with open(dfile, "w") as file:
		file.write("""
		ARG REGISTRY=""
		ARG TAG=""
		FROM ${REGISTRY}ignishpc/common${TAG}
		""")
		for core in cores:
			builder = default_registry + "ignishpc/" + core + "-builder:" + version
			file.write("COPY --from=" + builder + " ${IGNIS_HOME} ${IGNIS_HOME}\n")
			file.write("RUN 	${IGNIS_HOME}/bin/ignis-" + core + "-install.sh && ")
			file.write("rm -f ${IGNIS_HOME}/bin/ignis-" + core + "-install.sh\n")

		if driver:
			file.write("RUN ${IGNIS_HOME}/common/driver-install.sh\n")

		if executor:
			file.write("RUN ${IGNIS_HOME}/common/executor-install.sh\n")

	return {
		"id": id,
		"name": default_registry + "ignishpc/" + id,
		"path": path,
		"dockerfile": dfile,
		"log": os.path.join(path, "build.log"),
		"version": version,
		"order": order,
	}
