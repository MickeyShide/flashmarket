#!/bin/sh
set -eu

swap_file=/swapfile
sysctl_file=/etc/sysctl.d/99-flashmarket-memory.conf

if [ "$(id -u)" -ne 0 ]; then
  echo "install-host-memory-protection.sh must run as root" >&2
  exit 1
fi

if [ -e "$swap_file" ]; then
  swap_type=$(blkid -p -s TYPE -o value "$swap_file" 2>/dev/null || true)
  if [ "$swap_type" != "swap" ]; then
    echo "$swap_file exists but is not a swap area; refusing to overwrite it" >&2
    exit 1
  fi
else
  fallocate -l 2G "$swap_file"
  chmod 0600 "$swap_file"
  mkswap "$swap_file" >/dev/null
fi

chmod 0600 "$swap_file"
if ! swapon --show=NAME --noheadings | awk '{$1=$1};1' | grep -Fxq "$swap_file"; then
  swapon "$swap_file"
fi

if ! awk '$1 == "/swapfile" && $3 == "swap" { found=1 } END { exit !found }' /etc/fstab; then
  printf '%s\n' '/swapfile none swap sw 0 0' >> /etc/fstab
fi

printf '%s\n' 'vm.swappiness=10' > "$sysctl_file"
sysctl -p "$sysctl_file" >/dev/null

swapon --show=NAME --noheadings | awk '{$1=$1};1' | grep -Fxq "$swap_file"
[ "$(sysctl -n vm.swappiness)" = "10" ]

echo "Host memory protection active: $swap_file (2 GiB), vm.swappiness=10"
