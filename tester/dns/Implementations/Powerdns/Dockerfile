FROM ubuntu:noble

LABEL maintainer="sivakesava@cs.ucla.edu"

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ \
    git \
    make \
    pkg-config \
    libboost-all-dev \
    libtool \
    libssl-dev \
    libluajit-5.1-dev \
    python3-venv \
    autoconf \
    automake \
    ragel \
    bison \
    flex \
    libcurl4-openssl-dev \
    luajit \
    lua-yaml-dev \
    libyaml-cpp-dev \
    libtolua-dev \
    lua5.3 \
    gawk \
    libsqlite3-dev \
    libsodium-dev \
    default-libmysqlclient-dev \
    libpq-dev \
    libsystemd0 \
    libsystemd-dev \
    libmaxminddb-dev \
    libmaxminddb0 \
    libgeoip1 \
    libgeoip-dev \
    dnsutils \
    dos2unix \
    tzdata \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Clone PowerDNS
RUN git clone https://github.com/PowerDNS/pdns.git

ARG latest=false

# Optionally reset to fixed commit for reproducibility
RUN if [ "$latest" = "false" ] ; then \
        cd pdns && git reset --hard a03aaad7554483ee6efe72a81eda00a9d1a94fe5 ; \
    fi

# Build PowerDNS Authoritative Server
RUN cd pdns && \
    autoreconf -vi && \
    ./configure --with-modules="bind gsqlite3" --disable-lua-records --disable-systemd && \
    make -j$(nproc) && \
    make install

# Copy configuration files
COPY Powerdns/bindbackend.conf /usr/local/etc/
COPY Powerdns/pdns.conf /usr/local/etc/
COPY db.campus.edu /usr/local/etc/

# Convert configs to Unix line endings (in case host has CRLF)
RUN dos2unix /usr/local/etc/bindbackend.conf

# Run eternal loop (no daemon start inside build image)
CMD ["/bin/bash", "-c", "while :; do sleep 10; done"]
