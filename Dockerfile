FROM debian:12.11 AS build
LABEL maintainer="Richard Morley-Smith"

ENV JAVA_HOME="/usr/lib/jvm/java-11-openjdk"

RUN apk update && \
    apk add --no-cache \
            openjdk11~=11.0.23 \
            python3~=3.10.14 \
            py3-distutils-extra~=2.47 \
            make~=4.3 \
            g++~=12.2.1

WORKDIR /java-tree-sitter
COPY . ./

RUN python build.py -a ${ARCH}

FROM scratch AS export

WORKDIR /

COPY --from=build /java-tree-sitter/libjava-tree-sitter.so .
