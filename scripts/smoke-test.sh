#!/bin/sh
set -eu

base_url="${ECHO_BASE_URL:-http://localhost:8080}"

request() {
    path="$1"
    expected="$2"
    response="$(curl --fail --silent --show-error "${base_url}${path}")"
    echo "$response" | grep -F "$expected" >/dev/null
    printf 'ok  %s\n' "$path"
}

request "/api/v1/health/live/" '"status": "ok"'
request "/api/v1/health/ready/" '"status": "ok"'
request "/" "<!doctype html"

printf 'EchoMessenger HTTP smoke checks passed.\n'
