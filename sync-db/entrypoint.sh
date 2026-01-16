#!/bin/bash
set -e

ls -l ~/
gpgconf --kill all
echo "::group::Importing GPG key"
if [ ! -z "$gpg_key" ]; then
    echo "$gpg_key" | gpg --import
fi
echo "::endgroup::"

init_path=$PWD
python3 $init_path/sync-db/sync_database.py