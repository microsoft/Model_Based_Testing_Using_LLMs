FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y git dnsutils \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /src

# Clone both repos as siblings (TechnitiumLibrary must be at ../TechnitiumLibrary relative to DnsServer)
RUN git clone https://github.com/TechnitiumSoftware/TechnitiumLibrary.git TechnitiumLibrary
RUN git clone https://github.com/TechnitiumSoftware/DnsServer.git DnsServer

# Build only the TechnitiumLibrary projects that DnsServer needs (not the full solution with Windows-only projects)
WORKDIR /src/TechnitiumLibrary
RUN dotnet build TechnitiumLibrary/TechnitiumLibrary.csproj -c Release
RUN dotnet build TechnitiumLibrary.IO/TechnitiumLibrary.IO.csproj -c Release
RUN dotnet build TechnitiumLibrary.ByteTree/TechnitiumLibrary.ByteTree.csproj -c Release
RUN dotnet build TechnitiumLibrary.Net/TechnitiumLibrary.Net.csproj -c Release
RUN dotnet build TechnitiumLibrary.Security.Cryptography/TechnitiumLibrary.Security.Cryptography.csproj -c Release
RUN dotnet build TechnitiumLibrary.Security.OTP/TechnitiumLibrary.Security.OTP.csproj -c Release

# Now build DnsServer
WORKDIR /src/DnsServer
RUN dotnet publish DnsServerApp/DnsServerApp.csproj -c Release -o /app

# Runtime image
FROM mcr.microsoft.com/dotnet/aspnet:9.0

RUN apt-get update && apt-get install -y dnsutils \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir /etc/dns

COPY --from=build /app /opt/technitium/dns

WORKDIR /opt/technitium/dns

CMD ["/bin/bash", "-c", "while :; do sleep 10; done"]
