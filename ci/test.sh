#!/bin/bash

set -e

project_dir="$(dirname "$(dirname "$(readlink -f "${0}")")")"

export REGISTRY_BIN="${project_dir}/ci/tmp/registry"
export REGISTRY_DATA="${project_dir}/ci/tmp/registry-data"

set -x

reg_id=$(docker run -d registry:${1-2} sleep 1m)
docker cp $reg_id:/bin/registry "${REGISTRY_BIN}"
docker kill "${reg_id}"

mkdir -p "${REGISTRY_DATA}"

exec python ${project_dir}/setup.py test
