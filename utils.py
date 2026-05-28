import hashlib
import tarfile
import os

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def sha256_string(s):
    return hashlib.sha256(s.encode()).hexdigest()

def create_tar(source_dir, tar_path):
    with tarfile.open(tar_path, "w") as tar:
        for root, dirs, files in os.walk(source_dir):
            for name in sorted(files):
                full_path = os.path.join(root, name)
                arcname = os.path.relpath(full_path, source_dir)

                info = tar.gettarinfo(full_path, arcname)
                info.mtime = 0

                with open(full_path, "rb") as f:
                    tar.addfile(info, f)

def extract_tar(tar_path, dest):
    with tarfile.open(tar_path, "r") as tar:
        tar.extractall(dest)