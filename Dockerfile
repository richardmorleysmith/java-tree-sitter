FROM alpine:3.17.7 AS build

ARG ARCH
ENV JAVA_HOME="/usr/lib/jvm/java-11-openjdk"

RUN apk update && \
    apk add --no-cache  \
        g++ \
        make \
        openjdk11 \
        py3-distutils-extra \
        python3

WORKDIR /java-tree-sitter
COPY . ./

# Use clang instead of gcc and add sequential compilation
RUN apk add --no-cache clang && \
    CC=clang CXX=clang++ python build.py -s 'Linux' -a ${ARCH}

FROM scratch AS export

WORKDIR /

ARG ARCH
COPY --from=build /java-tree-sitter/libjava-tree-sitter-linux-${ARCH}.so .
