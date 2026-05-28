import os
import shutil
import json
import time
import hashlib
import tempfile
import subprocess
from utils import *

DOCK_DIR = os.path.expanduser("~/.docksmith")

def parse_file(path):
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]

def hash_dir(path):
    h = hashlib.sha256()

    if os.path.isfile(path):
        with open(path, "rb") as fp:
            h.update(fp.read())
        return h.hexdigest()

    for root, dirs, files in os.walk(path):
        for f in sorted(files):
            file_path = os.path.join(root, f)

            if "__pycache__" in file_path:
                continue

            try:
                with open(file_path, "rb") as fp:
                    h.update(fp.read())
            except:
                continue

    return h.hexdigest()

def get_cached_layer(cache_file):
    if not os.path.exists(cache_file):
        return None

    try:
        cached_digest = open(cache_file).read().strip()
        cached_layer_path = f"{DOCK_DIR}/layers/{cached_digest}.tar"

        if os.path.exists(cached_layer_path):
            return cached_digest
        else:
            return None
    except:
        return None

def build(tag, context, no_cache=False):
    lines = parse_file(os.path.join(context, "Docksmithfile"))

    temp_dir = os.path.join(tempfile.gettempdir(), "docksmith_build")

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(f"{DOCK_DIR}/layers", exist_ok=True)
    os.makedirs(f"{DOCK_DIR}/images", exist_ok=True)
    os.makedirs(f"{DOCK_DIR}/cache", exist_ok=True)

    layers = []
    prev_digest = ""
    env = {}
    workdir = "/"
    cmd = ""

    for step, line in enumerate(lines, start=1):
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

            source_path = os.path.expanduser(src)
            source_path = source_path if os.path.isabs(source_path) else os.path.join(context, source_path)

            dest_path = temp_dir + dest

            env_str = "".join([f"{k}={v}" for k, v in sorted(env.items())])

            if not os.path.exists(source_path):
                raise FileNotFoundError(f"Source path not found: {source_path}")

            file_hash = hash_dir(source_path)

            key = sha256_string(prev_digest + line + workdir + env_str + file_hash)
            cache_file = f"{DOCK_DIR}/cache/{key}"

            layer_digest = None

            if not no_cache:
                layer_digest = get_cached_layer(cache_file)

            if layer_digest:
                print("[CACHE HIT]")
            else:
                print("[CACHE MISS]")

                if os.path.isdir(source_path):
                    shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.copy2(source_path, dest_path)

                tar_path = os.path.join(tempfile.gettempdir(), "layer.tar")

                if os.path.exists(tar_path):
                    os.remove(tar_path)

                create_tar(temp_dir, tar_path)
                layer_digest = sha256_file(tar_path)

                shutil.move(tar_path, f"{DOCK_DIR}/layers/{layer_digest}.tar")

                with open(cache_file, "w") as f:
                    f.write(layer_digest)

            layers.append(layer_digest)
            prev_digest = layer_digest

        elif instr == "RUN":
            env_str = "".join([f"{k}={v}" for k, v in sorted(env.items())])

            key = sha256_string(prev_digest + line + workdir + env_str)
            cache_file = f"{DOCK_DIR}/cache/{key}"

            layer_digest = None

            if not no_cache:
                layer_digest = get_cached_layer(cache_file)

            if layer_digest:
                print("[CACHE HIT]")
            else:
                print("[CACHE MISS]")

                run_cmd = arg

                if run_cmd.startswith("/bin/echo"):
                    run_cmd = run_cmd.replace("/bin/echo", "echo")

                subprocess.run(run_cmd, shell=True, check=True)

                tar_path = os.path.join(tempfile.gettempdir(), "layer.tar")

                if os.path.exists(tar_path):
                    os.remove(tar_path)

                create_tar(temp_dir, tar_path)
                layer_digest = sha256_file(tar_path)

                shutil.move(tar_path, f"{DOCK_DIR}/layers/{layer_digest}.tar")

                with open(cache_file, "w") as f:
                    f.write(layer_digest)

            layers.append(layer_digest)
            prev_digest = layer_digest

        elif instr == "CMD":
            cmd = arg

    name, image_tag = tag.split(":")

    manifest = {
        "name": name,
        "tag": image_tag,
        "digest": "",
        "config": {
            "Env": env,
            "Cmd": cmd,
            "WorkingDir": workdir
        },
        "layers": [],
        "created": time.ctime()
    }

    for layer in layers:
        path = f"{DOCK_DIR}/layers/{layer}.tar"

        if not os.path.exists(path):
            continue

        size = os.path.getsize(path)

        manifest["layers"].append({
            "digest": f"sha256:{layer}",
            "size": size,
            "createdBy": "instruction"
        })

    manifest_bytes = json.dumps(manifest, sort_keys=True).encode()
    digest = hashlib.sha256(manifest_bytes).hexdigest()
    manifest["digest"] = f"sha256:{digest}"

    with open(f"{DOCK_DIR}/images/{name}_{image_tag}.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print("Build complete!")