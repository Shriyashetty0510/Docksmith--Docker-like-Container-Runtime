import os, shutil, json, time, hashlib
from utils import *

DOCK_DIR = os.path.expanduser("~/.docksmith")

def parse_file(path):
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]

# 🔥 NEW: hash directory for COPY cache
def hash_dir(path):
    h = hashlib.sha256()
    for root, dirs, files in os.walk(path):
        for f in sorted(files):
            file_path = os.path.join(root, f)
            try:
                with open(file_path, "rb") as fp:
                    h.update(fp.read())
            except:
                continue
    return h.hexdigest()

def build(tag, context, no_cache=False):
    lines = parse_file(os.path.join(context, "Docksmithfile"))

    temp_dir = "/tmp/docksmith_build"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    layers = []
    prev_digest = ""
    env = {}
    workdir = "/"

    step = 1

    for line in lines:
        parts = line.split(" ", 1)
        instr = parts[0]
        arg = parts[1] if len(parts) > 1 else ""

        print(f"Step {step}: {line}")

        if instr == "FROM":
            prev_digest = "base"

        elif instr == "WORKDIR":
            workdir = arg
            os.makedirs(temp_dir + workdir, exist_ok=True)

        elif instr == "ENV":
            k, v = arg.split("=")
            env[k] = v

        elif instr == "COPY":
            src, dest = arg.split()

            # expand ~
            src = os.path.expanduser(src)

            if os.path.isabs(src):
                source_path = src
            else:
                source_path = os.path.join(context, src)

            dest_path = temp_dir + dest

            # 🔥 CACHE KEY (CORRECT)
            env_str = "".join([f"{k}={v}" for k, v in sorted(env.items())])
            file_hash = hash_dir(source_path)

            key = sha256_string(prev_digest + line + workdir + env_str + file_hash)
            cache_file = f"{DOCK_DIR}/cache/{key}"

            if os.path.exists(cache_file) and not no_cache:
                print("[CACHE HIT]")
                layer_digest = open(cache_file).read()
            else:
                print("[CACHE MISS]")

                if os.path.isdir(source_path):
                    shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.copy2(source_path, dest_path)

                tar_path = "/tmp/layer.tar"
                create_tar(temp_dir, tar_path)
                layer_digest = sha256_file(tar_path)

                shutil.move(tar_path, f"{DOCK_DIR}/layers/{layer_digest}.tar")

                with open(cache_file, "w") as f:
                    f.write(layer_digest)

            layers.append(layer_digest)
            prev_digest = layer_digest

        elif instr == "RUN":
            # 🔥 EXECUTE inside container
            pid = os.fork()

            if pid == 0:
                os.chroot(temp_dir)
                os.chdir("/")
                parts = arg.split()
                os.execvp(parts[0], parts)
            else:
                os.wait()

            # 🔥 CACHE KEY
            env_str = "".join([f"{k}={v}" for k, v in sorted(env.items())])
            key = sha256_string(prev_digest + line + workdir + env_str)
            cache_file = f"{DOCK_DIR}/cache/{key}"

            if os.path.exists(cache_file) and not no_cache:
                print("[CACHE HIT]")
                layer_digest = open(cache_file).read()
            else:
                print("[CACHE MISS]")

                tar_path = "/tmp/layer.tar"
                create_tar(temp_dir, tar_path)
                layer_digest = sha256_file(tar_path)

                shutil.move(tar_path, f"{DOCK_DIR}/layers/{layer_digest}.tar")

                with open(cache_file, "w") as f:
                    f.write(layer_digest)

            layers.append(layer_digest)
            prev_digest = layer_digest

        elif instr == "CMD":
            cmd = arg

        step += 1

    name, tag = tag.split(":")

    manifest = {
        "name": name,
        "tag": tag,
        "layers": layers,
        "config": {
            "Env": env,
            "Cmd": cmd,
            "WorkingDir": workdir
        },
        "created": time.ctime()
    }

    os.makedirs(f"{DOCK_DIR}/images", exist_ok=True)

    with open(f"{DOCK_DIR}/images/{name}_{tag}.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print("Build complete!")
