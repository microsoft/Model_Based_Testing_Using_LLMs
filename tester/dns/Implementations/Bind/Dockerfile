FROM ubuntu:noble

LABEL maintainer="sivakesava@cs.ucla.edu"

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    pkg-config \
    python3 \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    meson \
    ninja-build \
    perl \
    libssl-dev \
    liburcu-dev \
    libuv1-dev \
    libcap-dev \
    libnghttp2-dev \
    libedit-dev \
    liblmdb-dev \
    libidn2-dev \
    zlib1g-dev \
    tzdata \
    ca-certificates \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Clone BIND
RUN git clone https://gitlab.isc.org/isc-projects/bind9.git

ARG latest=false

# Build BIND
RUN cd bind9 && \
    if [ "$latest" = "true" ]; then \
        echo "⚡ Building BIND with Meson..." && \
        meson setup build --prefix=/usr/local --sysconfdir=/usr/local/etc --localstatedir=/usr/local/var && \
        meson compile -C build && \
        meson install -C build ; \
    else \
        echo "📌 Building old BIND with Autotools..." && \
        autoreconf -fi && ./configure && \
        make -j$(nproc) && make install ; \
    fi && \
    ldconfig

# Generate rndc key
RUN cd /usr/local/etc && rndc-confgen -a

# Copy configuration files
COPY Bind/named.conf /usr/local/etc/
COPY db.campus.edu /usr/local/etc/

# Run eternal loop
CMD ["/bin/bash", "-c", "while :; do sleep 10; done"]
