#!/bin/bash
set -e

init_path=$PWD

echo "$RCLONE_CONFIG_NAME"

if [ ! -f ~/.config/rclone/rclone.conf ]; then
    mkdir --parents ~/.config/rclone
    echo "$RCLONE_CONFIG_CONTENT" >> ~/.config/rclone/rclone.conf
fi

echo "::group::Uploading to remote"
python3 $init_path/upload/upload.py 
echo "::endgroup::"