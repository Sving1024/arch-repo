#!/usr/bin/python3

import subprocess
import sys
import os
import tarfile
import shutil
import glob
import pyalpm
from typing import NamedTuple
from contextlib import suppress
import pathlib

REPO_NAME = os.environ["repo_name"]
ROOT_PATH = os.environ["dest_path"]
CONFIG_NAME = os.environ.get("RCLONE_CONFIG_NAME", "")

if CONFIG_NAME == "":
    result = subprocess.run(["rclone", "listremotes"], capture_output=True)
    CONFIG_NAME = result.stdout.decode().split("\n")[0]
if not CONFIG_NAME.endswith(":"):
    CONFIG_NAME = CONFIG_NAME + ":"

if ROOT_PATH.startswith("/"):
    ROOT_PATH = ROOT_PATH[1:]


class PkgInfo(NamedTuple):
    filename: str
    pkgname: str
    version: str


def get_pkg_infos(file_path: str) -> list["PkgInfo"]:
    """Get packages info from "*.db.tar.gz".

    Args:
        file_path (str): DB file path.

    Returns:
        list["PkgInfo"]: A list contains all packages info.
    """
    with tarfile.open(file_path) as f:
        f.extractall("/tmp/extractdb")

    pkg_infos = []
    pkgs = glob.glob("/tmp/extractdb/*/desc")
    for pkg_desc in pkgs:
        with open(pkg_desc, "r") as f:
            lines = f.readlines()
        lines = [i.strip() for i in lines]
        for index, line in enumerate(lines):
            if "%FILENAME%" in line:
                filename = lines[index + 1]
            if "%NAME%" in line:
                pkgname = lines[index + 1]
            if "%VERSION%" in line:
                version = lines[index + 1]

        pkg_infos.append(PkgInfo(filename=filename, pkgname=pkgname, version=version))

    shutil.rmtree("/tmp/extractdb")

    return pkg_infos


def rclone_download(name: str, dest_path: str = "./"):
    r = subprocess.run(
        [
            "rclone",
            "copy",
            f"{CONFIG_NAME}/{ROOT_PATH}/{name}",
            dest_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode())


def get_old_packages(
    local_packages: list["PkgInfo"], remote_packages: list["PkgInfo"]
) -> list["PkgInfo"]:
    old_packages = []
    for l in local_packages:
        for r in remote_packages:
            if l.pkgname == r.pkgname:
                res = pyalpm.vercmp(l.version, r.version)
                if res > 0:
                    old_packages.append(r)

    return old_packages


def download_local_miss_files(
    local_packages: list["PkgInfo"],
    remote_packages: list["PkgInfo"],
    old_packages: list["PkgInfo"],
):
    local_files = [i.filename for i in local_packages]
    remote_files = [i.filename for i in remote_packages]
    old_files = [i.filename for i in old_packages]
    remote_new_files = [i for i in remote_files if i not in old_files]
    for r in remote_new_files:
        if r not in local_files and ".db" not in r and ".files" not in r:
            with suppress(RuntimeError):
                rclone_download(r)
                rclone_download(r + ".sig")


if __name__ == "__main__":
    for pkg in pathlib.Path().glob("./*.tar.zst"):
        r = subprocess.run(
            ["repo-add", "/tmp/local_tmp.db.tar.gz", str(pkg)],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
    r = subprocess.run(
        ["rclone", "size", f"{CONFIG_NAME}/{ROOT_PATH}/{REPO_NAME}.db.tar.gz"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    remote_packages = None
    if r.returncode != 0 or "Total size: 0" in r.stdout.decode():
        print("Remote database file is not exist!")
        print(
            "If you are running this script for the first time, you can ignore this error."
        )
        print(r.stderr.decode())
        remote_packages = []
    else:
        rclone_download(f"{REPO_NAME}.db.tar.gz", "/tmp/")
        remote_packages = get_pkg_infos(f"/tmp/{REPO_NAME}.db.tar.gz")
    local_packages = get_pkg_infos("/tmp/local_tmp.db.tar.gz")

    old_packages = get_old_packages(local_packages, remote_packages)

    print("::group::Download missing files")
    download_local_miss_files(local_packages, remote_packages, old_packages)
    print("::endgroup::")
    print("::group::Signing packages")
    for pkg in local_packages:
        subprocess.run(
            ["gpg", "--detach-sig", "--yes", str(pkg.filename)],
            stderr=sys.stderr.fileno(),
            stdout=sys.stdout.fileno(),
        )
    print("::endgroup::")
    print("::group::Adding packages to repo")
    for pkg in pathlib.Path().glob("./*.tar.zst"):
        subprocess.run(
            ["repo-add", "--verify", "--sign", f"{REPO_NAME}.db.tar.gz", str(pkg)],
            stderr=sys.stderr.fileno(),
            stdout=sys.stdout.fileno(),
        )
    print("::endgroup::")
