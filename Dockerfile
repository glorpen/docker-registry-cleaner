FROM python:3.6-alpine as base

LABEL maintainer="Arkadiusz Dzięgiel <arkadiusz.dziegiel@glorpen.pl>"

FROM base as data

ADD src/ /root/app/src/
ADD README.rst CHANGES.rst setup.py /root/app/
RUN pip install --no-cache-dir --root /root/image --no-warn-script-location /root/app

FROM registry:2 as reg

FROM base

COPY --from=reg /bin/registry /bin/
COPY --from=data /root/image /
