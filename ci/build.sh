#!/bin/bash

project_dir="$(dirname "$(dirname "$(realpath "${0}")")")"

TAG="${1-latest}"
REGISTRY_TAG="${2-2}"
DOCKERFILE="${project_dir}/ci/tmp/Dockerfile"

set -ex

sed ${project_dir}/Dockerfile.tpl -e "s/{REGISTRY_TAG}/${REGISTRY_TAG}/g" > "${DOCKERFILE}"

exec docker build -f "${DOCKERFILE}" -t glorpen/docker-registry-cleaner:${TAG} "${project_dir}"
