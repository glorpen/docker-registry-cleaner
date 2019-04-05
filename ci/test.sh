#!/bin/bash

project_dir="$(dirname "$(dirname "$(realpath "${0}")")")"

export REGISTRY_BIN="${project_dir}/ci/tmp/registry"
export REGISTRY_DATA="${project_dir}/ci/tmp/registry-data"

set -ex

reg_id=$(docker run -d registry:${1-2} sleep 1m)
docker cp $reg_id:/bin/registry "${REGISTRY_BIN}"
docker kill "${reg_id}"

mkdir -p "${REGISTRY_DATA}"

exec python ${project_dir}/setup.py test
