FROM ubuntu:jammy

LABEL maintainer="sivakakarla@microsoft.com"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update 

RUN apt-get install -y \
  dnsutils \
  git \
  python3 \
  python3-pip \
  vim 

RUN git clone https://github.com/twisted/twisted.git

RUN cd twisted && \
    git reset --hard 157cd8e659705940e895d321339d467e76ae9d0a && \
    sed -i 's/self.origin = nativeString(fp.basename() + b".")/self.origin = nativeString(fp.basename() + ".")/' src/twisted/names/authority.py && \
    pip3 install -e .

COPY db.campus.edu /campus.edu.

# Run eternal loop
CMD ["/bin/bash", "-c", "while :; do sleep 10; done"]