#!/bin/bash
set -e

init_path=$PWD

if [[ -d ${HOME}/.gnupg ]]; then
    rm -rf ${HOME}/.gnupg
fi

mkdir -p ~/.gnupg
chmod 700 ~/.gnupg

echo "pinentry-mode loopback" > ~/.gnupg/gpg.conf
echo "allow-loopback-pinentry" > ~/.gnupg/gpg-agent.conf

echo "::group::Importing GPG key"
if [ ! -z "$gpg_key" ]; then
    echo "$gpg_key" | gpg --import --verbose --debug-all
fi
echo "::endgroup::"

python3 $init_path/create-db/create_db.py