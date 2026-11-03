#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Run as root." >&2
    exit 1
fi

source_dir=/home/vmagent/.vscode/extensions/kilocode.kilo-code-7.8.1
if [ ! -d "$source_dir" ]; then
    echo "Installed Kilo extension directory not found: $source_dir" >&2
    exit 1
fi

for account in agent-wide agent-limited; do
    destination="/home/$account/.vscode/extensions/kilocode.kilo-code-7.8.1"
    if [ -e "$destination" ]; then
        echo "Refusing to overwrite existing extension for $account: $destination" >&2
        exit 1
    fi
    cp -a "$source_dir" "$destination"
    chown -R "$account:$account" "$destination"
done

printf '%s\n' 'Copied the installed Kilo extension code only. No user profile or credential storage was copied.'
