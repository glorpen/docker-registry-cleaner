#!/bin/bash

set -e

project_dir="$(dirname "$(dirname "$(readlink -f "${0}")")")"

if [ "x${1}" == "x" ];
then
	echo "You have to specify image name as first argument"
	exit 1
fi

set -x

exec docker run --rm \
-u $UID:$UID -w /srv \
-e HOME="/srv" \
-v "${project_dir}:/srv" \
--tmpfs /var/lib/registry \
${1} \
python /srv/setup.py test
