#!/usr/bin/env python3

from __future__ import print_function

from sys import stdout
from time import sleep

messages = [
    'announce route 100.10.0.0/24 next-hop self as-path [100 64512]',
]

sleep(5)

#Iterate through messages
for message in messages:
    stdout.write(message + '\n')
    stdout.flush()
    sleep(1)

#Loop endlessly to allow ExaBGP to continue running
while True:
    sleep(1)