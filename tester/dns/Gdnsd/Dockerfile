FROM ubuntu:bionic

LABEL maintainer="sivakakarla@microsoft.com"

RUN apt-get update 

RUN apt-get install -y \
    autoconf \
    automake \
    cpanminus \
    dnsutils \
    gcc \
    git \
    libev-dev \
    libsodium-dev \
    liburcu-dev \
    make \
    ragel \
    vim 

# RUN cpanm Test::More JSON::PP Socket6 IO::Socket::INET6 HTTP::Daemon Net::DNS

RUN git clone https://github.com/gdnsd/gdnsd.git

RUN cd gdnsd && \
    git reset --hard 877e15cf55593fa618d2009027e928d5f52da775 && \
    autoreconf -vif && \
    ./configure && \
    make install

COPY db.campus.edu /usr/local/etc/gdnsd/zones/campus.edu.

# Run eternal loop
CMD ["/bin/bash", "-c", "while :; do sleep 10; done"]