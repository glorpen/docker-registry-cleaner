#!/bin/bash

set -e

project_dir="$(dirname "$(dirname "$(readlink -f "${0}")")")"

sed ${project_dir}/Dockerfile.tpl -e "s/{REGISTRY_TAG}/${1-2}/g"
