#!/bin/bash
set -e

init_path=$PWD
mkdir upload_packages
find $local_path -type f -name "*.tar.zst" -exec cp {} ./upload_packages/ \;

if [ ! -f ~/.config/rclone/rclone.conf ]; then
    mkdir --parents ~/.config/rclone
    echo "[R2]" >> ~/.config/rclone/rclone.conf
    echo "type = s3" >> ~/.config/rclone/rclone.conf
    echo "provider = Cloudflare" >> ~/.config/rclone/rclone.conf
    echo "access_key_id=$RCLONE_S3_ACCESS_KEY_ID" >> ~/.config/rclone/rclone.conf
    echo "secret_access_key=$RCLONE_S3_SECRET_KEY" >> ~/.config/rclone/rclone.conf
    echo "endpoint=$RCLONE_S3_ENDPOINT" >> ~/.config/rclone/rclone.conf
fi

if [ ! -z "$gpg_key" ]; then
    echo "$gpg_key" | gpg --import
fi

cd upload_packages || exit 1

repo-add "./${repo_name:?}.db.tar.gz" ./*.tar.zst
python3 $init_path/create-db-and-upload-action/sync.py
rm "./${repo_name:?}.db.tar.gz"
rm "./${repo_name:?}.files.tar.gz"

if [ ! -z "$gpg_key" ]; then
    packages=( "*.tar.zst" )
    for name in $packages
    do
        gpg --detach-sig --yes $name
    done
    repo-add --verify --sign "./${repo_name:?}.db.tar.gz" ./*.tar.zst
fi
rclone copy ./ "R2:${dest_path:?}" --copy-links
