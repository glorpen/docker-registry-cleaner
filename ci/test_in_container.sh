#!/bin/bash

project_dir="$(dirname "$(dirname "$(realpath "${0}")")")"

set -ex

bash "${project_dir}/ci/build.sh" "latest" "${1-2}"

exec docker run --rm \
-u $UID:$UID -w /srv \
-e PYTHONPATH="/srv/src" -e HOME="/srv" \
-v "${project_dir}:/srv" \
--tmpfs /var/lib/registry \
glorpen/docker-registry-cleaner:latest \
python /srv/setup.py test
