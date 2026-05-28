#!/usr/bin/env python3

import sys
sys.path.append("/root/docksmith")

import argparse
import os
import json
from builder import build
from runtime import run_image

DOCK_DIR = os.path.expanduser("~/.docksmith")

parser = argparse.ArgumentParser()
parser.add_argument("command")
parser.add_argument("-t", "--tag")
parser.add_argument("--no-cache", action="store_true")
parser.add_argument("-e", action="append")

args = parser.parse_args()

if args.command == "build":
    build(args.tag, ".", args.no_cache)

elif args.command == "run":
    env = {}
    if args.e:
        for item in args.e:
            k, v = item.split("=")
            env[k] = v

    run_image(args.tag, env)

elif args.command == "images":
    images_dir = f"{DOCK_DIR}/images"

    if not os.path.exists(images_dir):
        print("No images found.")
    else:
        print("NAME\tTAG\tID\t\tCREATED")

        for file in os.listdir(images_dir):
            path = os.path.join(images_dir, file)

            with open(path) as f:
                data = json.load(f)

            digest = data.get("digest", "")
            short_id = digest.replace("sha256:", "")[:12]

            print(f"{data['name']}\t{data['tag']}\t{short_id}\t{data['created']}")

elif args.command == "rmi":
    name, tag = args.tag.split(":")
    image_path = f"{DOCK_DIR}/images/{name}_{tag}.json"

    if not os.path.exists(image_path):
        print("Image not found")
        exit()

    with open(image_path) as f:
        data = json.load(f)

    for layer in data["layers"]:
        digest = layer["digest"].replace("sha256:", "")
        layer_path = f"{DOCK_DIR}/layers/{digest}.tar"

        if os.path.exists(layer_path):
            os.remove(layer_path)

    os.remove(image_path)
    print(f"Removed image {args.tag}")