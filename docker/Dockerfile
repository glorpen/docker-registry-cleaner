FROM python:3.6-alpine as base

LABEL maintainer="Arkadiusz Dzięgiel <arkadiusz.dziegiel@glorpen.pl>"

RUN pip --no-cache-dir install pyyaml requests natsort semver py-expression-eval

#ADD docker/entrypoint.py /usr/local/bin/docker-entrypoint
#ARG HOSTDNS_VERSION=
#ENTRYPOINT ["/usr/local/bin/docker-entrypoint"]

FROM base as data

ADD src/ /root/app/src/
ADD README.rst CHANGES.rst setup.py /root/app/
RUN pip install --no-cache-dir --root /root/image /root/app

FROM base

COPY --from=data /root/image /
