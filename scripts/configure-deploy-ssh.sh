#!/usr/bin/env bash
set -Eeuo pipefail

: "${DEPLOY_HOST:?DEPLOY_HOST is required}"
: "${DEPLOY_PORT:?DEPLOY_PORT is required}"
: "${SSH_PRIVATE_KEY:?DEPLOY_SSH_KEY is required}"
: "${SSH_KNOWN_HOSTS:?DEPLOY_KNOWN_HOSTS is required}"

ssh_dir="${HOME}/.ssh"
install -d -m 700 "$ssh_dir"
printf '%s\n' "$SSH_PRIVATE_KEY" > "$ssh_dir/id_ed25519"
printf '%s\n' "$SSH_KNOWN_HOSTS" > "$ssh_dir/known_hosts"
chmod 600 "$ssh_dir/id_ed25519" "$ssh_dir/known_hosts"

host_lookup="$DEPLOY_HOST"
if [[ "$DEPLOY_PORT" != "22" ]]; then
  host_lookup="[$DEPLOY_HOST]:$DEPLOY_PORT"
fi
if ! ssh-keygen -F "$host_lookup" -f "$ssh_dir/known_hosts" >/dev/null; then
  echo "::error::DEPLOY_KNOWN_HOSTS has no key for $host_lookup"
  exit 1
fi

cat > "$ssh_dir/config" <<'EOF'
Host *
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    StrictHostKeyChecking yes
    UserKnownHostsFile ~/.ssh/known_hosts
    ConnectTimeout 15
    ServerAliveInterval 15
    ServerAliveCountMax 4
EOF
chmod 600 "$ssh_dir/config"
