FROM python:3.6-alpine as base

LABEL maintainer="Arkadiusz Dzięgiel <arkadiusz.dziegiel@glorpen.pl>"

FROM base as data

ADD src/ /root/app/src/
ADD README.rst setup.py /root/app/
RUN pip install --no-cache-dir --root /root/image --no-warn-script-location /root/app

FROM base

COPY --from=registry:{REGISTRY_TAG} /bin/registry /bin/
COPY --from=data /root/image /
