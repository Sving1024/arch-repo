Use GitHub Actions to build Arch packages.
For more information, please read [my post](https://viflythink.com/Use_GitHubActions_to_build_AUR/) (Chinese).

The uploadToOneDrive job is optional, you can use [urepo](https://github.com/vifly/urepo) to create your package repositorie after upload to OneDrive.

# Usage
The packages are located at OneDrive and GitHub releases, choose one of you like.

Add the following code snippet to your `/etc/pacman.conf`:

```
# Download from OneDrive
[archlinux-sving1024]
Server = https://repo.sving1024.top/api/raw?path=/
```

Then, run `sudo pacman -Syu` to update repository and upgrade system.

Now you can use `sudo pacman -S <pkg_name>` to install packages from my repository.

# TODO
- [ ] some actions are too coupled, need to refactor
- [ ] add more clear output log for debug
