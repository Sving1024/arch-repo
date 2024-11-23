#!/usr/bin/python3

import asyncio
import asyncio.taskgroups
import os
import tarfile
import shutil
import glob
from typing import NamedTuple
from contextlib import suppress
import pyalpm

REPO_NAME = os.environ["repo_name"]
ROOT_PATH = os.environ["dest_path"]
CONFIG_NAME = os.environ.get("RCLONE_CONFIG_NAME", "")

if CONFIG_NAME == "":
    remotes = asyncio.run(
        asyncio.create_subprocess_exec("rclone", "listremotes", capture_output=True)
    )
    CONFIG_NAME = remotes.stdout.decode().split("\n")[0]
if not CONFIG_NAME.endswith(":"):
    CONFIG_NAME = CONFIG_NAME + ":"

if ROOT_PATH.startswith("/"):
    ROOT_PATH = ROOT_PATH[1:]


class remote:
    config_name: str

    def __init__(self, confg_name: str) -> None:
        self.config_name = confg_name

    async def delete(self, name: str):
        print(f"removing {name}")
        res = await asyncio.create_subprocess_exec(
            "rclone",
            "delete",
            f"{self.config_name}/{ROOT_PATH}/{name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        if res.returncode != 0:
            raise RuntimeError(res.stderr.decode())
        print(f"complete removing {name}")

    async def download(self, name: str, dest_path: str = "./"):
        res = await asyncio.create_subprocess_exec(
            "rclone",
            "copy",
            f"{CONFIG_NAME}/{ROOT_PATH}/{name}",
            dest_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        if res.returncode != 0:
            raise RuntimeError(res.stderr.decode())


class PkgInfo(NamedTuple):
    filename: str
    pkgname: str
    version: str


storage = remote(CONFIG_NAME)


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

        pkg_infos.append(PkgInfo(filename, pkgname, version))

    shutil.rmtree("/tmp/extractdb")

    return pkg_infos


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
                storage.download(r)


async def run():
    result = asyncio.run(
        asyncio.create_subprocess_exec(
            "rclone",
            "size",
            f"{CONFIG_NAME}/{ROOT_PATH}/{REPO_NAME}.db.tar.gz",
            stderr=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
        )
    )
    if result.returncode != 0 or "Total size: 0" in result.stdout.decode():
        print("Remote database file is not exist!")
        print(
            "If you are running this script for the first time, you can ignore this error."
        )
        print(result.stderr.decode())
        exit(0)

    local_packages = get_pkg_infos(f"./{REPO_NAME}.db.tar.gz")

    storage.download(f"{REPO_NAME}.db.tar.gz", "/tmp/")
    remote_packages = get_pkg_infos(f"/tmp/{REPO_NAME}.db.tar.gz")

    old_packages = get_old_packages(local_packages, remote_packages)
    async with asyncio.TaskGroup() as tg:
        for i in old_packages:
            tg.create_task(storage.delete(i.filename))
            with suppress(RuntimeError):
                tg.create_task(storage.delete(i.filename + ".sig"))

    download_local_miss_files(local_packages, remote_packages, old_packages)


if __name__ == "__main__":
    asyncio.run(run())
