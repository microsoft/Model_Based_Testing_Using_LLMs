FROM ubuntu:noble

LABEL maintainer="sivakesava@cs.ucla.edu"

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    automake \
    autoconf \
    libtool \
    bison \
    flex \
    gcc \
    g++ \
    git \
    make \
    libssl-dev \
    libevent-dev \
    pkg-config \
    dnsutils \
    ca-certificates \
    vim \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Clone NSD
RUN git clone https://github.com/NLnetLabs/nsd.git

ARG latest=false

RUN if [ "$latest" = "false" ] ; then \
        cd nsd && git reset --hard 4043a5ab7be7abaec969011e48e4d0d60a0056a6 ; \
    fi

# Build (disable dnstap so protoc isn’t needed)
RUN cd nsd && \
    git submodule update --init && \
    autoreconf -fi && \
    ./configure --disable-dnstap && \
    make -j$(nproc) && \
    make install && \
    ldconfig

# Copy configuration files
COPY Nsd/nsd.conf /etc/nsd/
COPY db.campus.edu /etc/nsd/zones/

# Setup nsd-control
RUN nsd-control-setup

# Run eternal loop
CMD ["/bin/bash", "-c", "while :; do sleep 10; done"]
