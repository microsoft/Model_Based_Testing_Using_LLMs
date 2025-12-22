## Building Docker images for BGP implementations

Download all the images from this [link](https://drive.google.com/drive/folders/1fEns5tyxdOZLbICibMnvN71Ucjl2tl89).

### GoBGP
```bash
$ unzip ksator_gobgp.zip
$ mv ksator_gobgp.tar.gz ksator_gobgp.tar
$ docker load -i ksator_gobgp.tar
$ docker tag ksator_gobgp:latest ksator/gobgp:1.0
```

### FRR
```bash
$ unzip github_frr10.zip
$ mv github_frr10.tar.gz github_frr10.tar
$ docker load -i github_frr10.tar
$ docker tag github_frr10 github/frr10
```

### ExaBGP
```bash
$ unzip mikenowak_exabgp.zip
$ mv mikenowak.tar.gz mikenowak_exabgp.tar
$ docker load -i mikenowak_exabgp.tar
$ docker tag mikenowak_exabgp:latest mikenowak/exabgp:latest
```

### Batfish
```bash
$ docker pull batfish/allinone
```