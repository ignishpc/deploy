import datetime
import os
import re
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from distutils.version import StrictVersion

import docker
import docker.errors

try:
    import git

    GIT_ERROR = None
except Exception as ex:
    GIT_ERROR = ex

MODULE_NAME = "images"


def clear(yes, version, whitelist, blacklist, add_none, force, default_registry, namespace):
    client = docker.from_env()
    images = __getImages(client, version, default_registry, namespace, whitelist, blacklist, none=add_none)
    images.sort(key=lambda x: x[2], reverse=True)

    print("Following images will be cleared:")
    print("IMAGE ID       CREATED          TAG")
    now = datetime.datetime.now()
    for img_id, img_tag, created in images:
        print(img_id[7:19], " ", __dateFormat(now - created), img_tag if img_tag is not None else "<none>")
    if not yes:
        option = input("Are you sure (yes/no): ")
        while option not in ["yes", "no"]:
            option = input("Please type yes/no: ")
        yes = option == "yes"
    if yes:
        for img_id, img_tag, _ in images:
            try:
                client.images.remove(image=img_tag if img_tag is not None else img_id, force=force)
            except docker.errors.APIError as ex:
                print(img_id[7:19], "can't be removed:", ex.explanation)
    else:
        print("Aborted")


def push(yes, builders, version, whitelist, blacklist, default_registry, namespace):
    client = docker.from_env()
    images = __getImages(client, version, default_registry, namespace, whitelist, blacklist)
    images.sort(key=lambda x: x[2])
    if not builders:
        builder = re.compile(".*\/.*-?builder(:.+)?")
        images = list(filter(lambda img: not builder.match(img[1]), images))

    print("Following images will be pushed:")
    print("IMAGE ID       CREATED          TAG")
    now = datetime.datetime.now()
    for img_id, img_tag, created in images:
        print(img_id[7:19], " ", __dateFormat(now - created), img_tag if img_tag is not None else "<none>")
    if not yes:
        option = input("Are you sure (yes/no): ")
        while option not in ["yes", "no"]:
            option = input("Please type yes/no: ")
        yes = option == "yes"
    if yes:
        for _, img_tag, _ in images:
            client = docker.from_env()
            for line in client.images.push(img_tag, stream=True, decode=True):
                if 'errorDetail' in line:
                    print("Aborting")
                    raise docker.errors.APIError(line['errorDetail']['message'])
            print(img_tag, "PUSHED")


def build(sources, local_sources, ignore_folders, version_filters, custom_images, bases, full, save_logs, version_tags,
          version, default_registry, namespace):
    with tempfile.TemporaryDirectory(prefix="ignis") as wd:
        core_list = list()
        version_map = dict()
        for vf in version_filters:
            version_map[vf[0]] = vf[1]

        tmp = os.path.join(wd, "tmp")

        def prepare_sources(folder, local, duplicates):
            dockerfiles = os.path.join(folder, "Dockerfiles")
            if not os.path.exists(dockerfiles):
                print("warn: " + folder + " ignored, Dockerfiles folder not found")
                return
            subfolders = list(filter(lambda name: name not in ignore_folders, os.listdir(dockerfiles)))
            for core in subfolders:
                if core in duplicates:
                    raise RuntimeError(core + " is already defined")
                duplicates.add(core)
                core_folder = os.path.join(wd, core)
                if core == subfolders[-1] and not local:
                    os.rename(folder, core_folder)
                else:
                    shutil.copytree(folder, core_folder)

                v = __setVersion(core, core_folder, version_map.get(core, version))
                git_folder = os.path.join(core_folder, ".git")
                if os.path.exists(git_folder):
                    shutil.rmtree(git_folder, ignore_errors=True)
                print("  " + core + ":" + v)
                core_list.append((core_folder, v))

        print("Sources:")
        duplicates = set()
        if len(sources) > 0 and GIT_ERROR is not None:
            raise GIT_ERROR
        for src in sources:
            git.Repo.clone_from(src, tmp)
            prepare_sources(tmp, False, duplicates)

        for src in local_sources:
            prepare_sources(src, True, duplicates)

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
                    "name": default_registry + namespace + id,
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
                    __createDockerfile(wd, id + "-driver", ["driver", id], core["version"], default_registry,
                                       namespace, 200))
                build_list.append(
                    __createDockerfile(wd, id + "-executor", ["executor", id], core["version"], default_registry,
                                       namespace, 200))
                build_list.append(
                    __createDockerfile(wd, id if id != "common" else "common-full", ["driver", "executor", id],
                                       core["version"], default_registry, namespace, 201))

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
            build_list.append(
                __createDockerfile(wd, img[0], img[1:], custom_version, default_registry, namespace, i))

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
        image_list = list()
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
                            image_list.append((info, wait.result()))
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
                    default_registry=default_registry,
                    namespace=namespace
                )))
        print("Build end")
        if version_tags:
            print("Setting additional version tag:")
            for vt in version_tags:
                for info, img in image_list:
                    tag = info['name'] + ':' + vt
                    img.tag(tag)
                    print("  ", tag)



def __getImages(client, version, default_registry, namespace, whitelist, blacklist, none=False):
    labels = ["ignis"] if version is None else ["ignis=" + version]
    prefix = default_registry + namespace
    imgs = client.images.list(name=prefix + "*", filters={"label": labels})
    white_tags = set()
    black_tags = set()
    result = list()

    if whitelist is not None:
        for name in whitelist:
            if ":" in name:
                white_tags.add(name)
            else:
                white_tags.add(name + ":latest")
    for name in blacklist:
        if ":" in name:
            black_tags.add(name)
        else:
            black_tags.add(name + ":latest")

    for img in imgs:
        for tag in img.tags:
            if tag.startswith(prefix):
                name = tag[len(prefix):]
                if whitelist is not None and name not in white_tags:
                    continue
                if name in black_tags:
                    continue
                result.append((img.id, tag, __getDate(img)))

    if none:
        imgs = client.images.list(filters={"label": labels})
        root_nones = list(filter(lambda img: len(img.attrs['RepoTags']) == 0, imgs))
        layers = client.images.list(filters={"label": labels}, all=True)
        layer_map = dict()
        for layer in layers:
            layer_map[layer.id] = layer
        nones = list()
        while len(root_nones) > 0:
            none = root_nones.pop()
            nones.append(none)
            parent_id = none.attrs['Parent']
            if not parent_id or parent_id not in layer_map:
                continue
            parent = layer_map[parent_id]
            if len(parent.attrs['RepoTags']) == 0:
                root_nones.append(parent)

        for img in nones:
            if len(img.tags) > 0:
                for tag in img.tags:
                    result.append((img.id, tag))
            else:
                result.append((img.id, None, __getDate(img)))

    return result


def __getDate(img):
    sdate = img.attrs['Created']
    nano = sdate.split(".")[-1]
    sdate = sdate[0:-len(nano)] + nano[0:6] + 'Z'
    return datetime.datetime.strptime(sdate, '%Y-%m-%dT%H:%M:%S.%fZ')


def __dateFormat(elapsed):
    seconds = int(elapsed.total_seconds())
    periods = [
        ('year', 60 * 60 * 24 * 365),
        ('month', 60 * 60 * 24 * 30),
        ('day', 60 * 60 * 24),
        ('hour', 60 * 60),
        ('minute', 60),
        ('second', 1)
    ]
    for pname, pseconds in periods:
        if seconds > pseconds:
            value = int(seconds / pseconds)
            result = "{} {}{} {}".format(value, pname, 's' if value > 1 else '', "ago")
            result += " " * (16 - len(result))
            return result


def __is_git(path):
    if GIT_ERROR is not None:
        return False
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


def __setVersion(name, path, version):
    if version is None:
        return "latest"
    if not __is_git(path):
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


def __docker_build(name, path, dockerfile, log, version, default_registry, namespace):
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
                "NAMESPACE": namespace,
                "TAG": ":" + version,
                "RELPATH": os.path.relpath(os.path.dirname(dockerfile), path) + "/"
            }
        )
    except docker.errors.BuildError as ex:
        imageObj = None
        buildlog = ex.build_log
        error = ex
        manifest_error = re.compile(".*manifest for (.*) not found.*")
        result = manifest_error.search(ex.msg)
        if result:
            error = RuntimeError(result.group(1) + " required, use --sources or --local-source to add Dockerfile")
    except Exception as ex:
        imageObj = None
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


def __createDockerfile(wd, id, cores, version, default_registry, namespace, order=100):
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
        ARG NAMESPACE="ignishpc/"
        ARG TAG=""
        FROM ${REGISTRY}${NAMESPACE}common${TAG}
        ARG RELPATH=""
        """)
        for core in cores:
            builder = default_registry + namespace + core + "-builder:" + version
            file.write("COPY --from=" + builder + " ${IGNIS_HOME} ${IGNIS_HOME}\n")
            file.write("RUN 	${IGNIS_HOME}/bin/ignis-" + core + "-install.sh && ")
            file.write("rm -f ${IGNIS_HOME}/bin/ignis-" + core + "-install.sh\n")

        if driver:
            file.write("RUN ${IGNIS_HOME}/common/driver-install.sh\n")

        if executor:
            file.write("RUN ${IGNIS_HOME}/common/executor-install.sh\n")

    return {
        "id": id,
        "name": default_registry + namespace + id,
        "path": path,
        "dockerfile": dfile,
        "log": os.path.join(path, "build.log"),
        "version": version,
        "order": order,
    }
