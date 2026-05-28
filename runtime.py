import os
import shutil
import json
import tempfile
import subprocess
from utils import extract_tar

DOCK_DIR = os.path.expanduser("~/.docksmith")

def run_image(tag, env_override):
    name, image_tag = tag.split(":")
    image_path = f"{DOCK_DIR}/images/{name}_{image_tag}.json"

    with open(image_path) as f:
        data = json.load(f)

    temp_dir = os.path.join(tempfile.gettempdir(), "docksmith_run")

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    os.makedirs(temp_dir, exist_ok=True)

    # Extract layers
    for layer in data["layers"]:
        digest = layer["digest"].replace("sha256:", "")
        layer_path = f"{DOCK_DIR}/layers/{digest}.tar"

        if os.path.exists(layer_path):
            extract_tar(layer_path, temp_dir)

    env = os.environ.copy()
    env.update(data["config"].get("Env", {}))
    env.update(env_override)

    workdir = data["config"].get("WorkingDir", "/")
    full_workdir = os.path.join(temp_dir, workdir.lstrip("/"))

    os.makedirs(full_workdir, exist_ok=True)

    print("Running container...")

    cmd = eval(data["config"]["Cmd"])

    # Convert Linux-style paths to Windows-friendly paths
    converted_cmd = []

    for item in cmd:
        if item.startswith("/app/"):
            converted_item = os.path.join(temp_dir, item.lstrip("/").replace("/", os.sep))
            converted_cmd.append(converted_item)
        elif item == "/bin/sh":
            converted_cmd.append("cmd")
            converted_cmd.append("/c")
        else:
            converted_cmd.append(item)

    try:
        subprocess.run(
            converted_cmd,
            cwd=full_workdir,
            env=env,
            check=True,
            shell=False
        )
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)