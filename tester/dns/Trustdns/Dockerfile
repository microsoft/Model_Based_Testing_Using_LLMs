FROM ubuntu:22.04

LABEL maintainer="sivakakarla@microsoft.com"

RUN apt-get update 
RUN apt-get install -y \
    curl \
    openssl \
    libssl-dev \
    pkg-config \
    git \
    vim \
    build-essential

# Add nobody user and group for hickory-dns privilege dropping
RUN groupadd -f nobody && useradd -g nobody nobody || true 

RUN  curl https://sh.rustup.rs -sSf | sh -s -- -y

# trust-dns has been renamed to hickory-dns, clone and rename to trust-dns for compatibility
RUN git clone https://github.com/hickory-dns/hickory-dns.git trust-dns

ARG latest=false

# Use stable version tags instead of old commit hashes
RUN if [ "$latest" = "false" ] ; then cd trust-dns && git checkout v0.25.2 ; fi

RUN if [ "$latest" = "true" ] ; then cd trust-dns && git checkout main ; fi

RUN cd trust-dns && \
    /root/.cargo/bin/cargo build --release -p hickory-dns

COPY db.campus.edu trust-dns/tests/test-data/named_test_configs/
COPY Trustdns/config.toml trust-dns/tests/test-data/named_test_configs/

# Run eternal loop
CMD ["/bin/bash", "-c", "while :; do sleep 10; done"]