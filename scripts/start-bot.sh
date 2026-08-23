#!/bin/zsh

set -eu

script_dir=${0:A:h}
project_root=${script_dir:h}
venv_python="$project_root/.venv/bin/python"

if [[ -x "$venv_python" ]]; then
    python_command="$venv_python"
elif command -v python3 >/dev/null 2>&1; then
    python_command=$(command -v python3)
else
    print -u2 "Python 3 was not found. Install Python 3.9 or newer and try again."
    exit 1
fi

discord_token=""
token_source="hidden prompt"

cleanup() {
    unset DISCORD_TOKEN
    discord_token=""
}

trap cleanup EXIT HUP INT TERM

usage() {
    print "Usage: ./scripts/start-bot.sh [--clipboard]"
    print "  --clipboard  Read the Discord token from the macOS clipboard."
}

case "${1:-}" in
    "")
        printf "Paste Discord Bot Token with Command+V (input stays hidden), then press Return: "
        IFS= read -r -s discord_token
        printf "\n"
        ;;
    --clipboard)
        if (( $# != 1 )); then
            usage >&2
            exit 1
        fi
        discord_token=$(/usr/bin/pbpaste)
        token_source="clipboard"
        ;;
    -h|--help)
        usage
        exit 0
        ;;
    *)
        usage >&2
        exit 1
        ;;
esac

if [[ -z "${discord_token//[[:space:]]/}" ]]; then
    print -u2 "A Discord bot token was not found in the $token_source."
    exit 1
fi

printf "Discord bot token received from %s (%d characters). Starting Cody...\n" \
    "$token_source" "${#discord_token}"

export DISCORD_TOKEN="$discord_token"
discord_token=""

cd "$project_root"
"$python_command" main.py
