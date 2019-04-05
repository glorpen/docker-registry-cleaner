#!/bin/bash

set -e

project_dir="$(dirname "$(dirname "$(readlink -f "${0}")")")"

TAG="${1-latest}"
REGISTRY_TAG="${2-2}"
DOCKERFILE="${project_dir}/ci/tmp/Dockerfile"

set -x

sed ${project_dir}/Dockerfile.tpl -e "s/{REGISTRY_TAG}/${REGISTRY_TAG}/g" > "${DOCKERFILE}"

exec docker build -f "${DOCKERFILE}" -t glorpen/docker-registry-cleaner:${TAG} "${project_dir}"
