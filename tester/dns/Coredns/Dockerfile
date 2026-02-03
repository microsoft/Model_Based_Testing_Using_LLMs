FROM golang:1.20

RUN apt-get update 

RUN git clone https://github.com/coredns/coredns

ARG latest=false

RUN if [ "$latest" = "false" ] ; then cd coredns && git reset --hard 6edc8fe7f6c2f57844c8ee7f7f5deef71085ebe8 ; fi

RUN if [ "$latest" = "true" ] ; then cd coredns && git reset --hard 45923b6e12a2eabaf55d7380e6df4e7354a1207d ; fi

RUN cd coredns && \
    make

COPY db.campus.edu /go/coredns
COPY Coredns/Corefile /go/coredns

WORKDIR /go/coredns
# Run eternal loop
CMD ["/bin/bash", "-c", "while :; do sleep 10; done"] 