# Testing different server implementations

tests.json: copied from smtp_complete_tests.json

tester.py: Looping over test cases, uses smtplib to run the test cases on different servers

server1 : implementaion using aiosmtpd

server2 : implementation using smtpd

server3: implementation using OpenSMTPD

Installation:

sudo apt install opensmtpd
Run Locally:
Edit the configuration file (/etc/smtpd.conf) to bind to localhost:

listen on localhost port 8025

Start the server:

sudo smtpd -d

Debug:

1. Check for Running Instances
Ensure no other instances of OpenSMTPD are running:

ps aux | grep smtpd
If you see a running process for smtpd, stop it:

sudo pkill smtpd

2. Check the Control Socket
OpenSMTPD uses a control socket file (e.g., /var/run/smtpd.sock) for inter-process communication. If this file is not cleaned up after a crash, it can block a new instance from starting.

Find the control socket file:

ls /var/run/ | grep smtpd
Delete the socket file (if it exists):

sudo rm /var/run/smtpd.sock

3. Start OpenSMTPD Manually
Restart OpenSMTPD to ensure it works correctly:

sudo smtpd -dv

4. Check Configuration
If the issue persists, verify that the configuration file /etc/smtpd.conf is valid:

sudo smtpctl check
If there’s an error, fix the configuration file.

5. Check System Logs
For more details, check the system logs:

sudo journalctl -u smtpd
6. Reinstall OpenSMTPD (Optional)
If the above steps don’t resolve the issue, you may need to reinstall OpenSMTPD:

sudo apt remove --purge opensmtpd
sudo apt install opensmtpd

Testing:
You can now connect to the server using smtplib in Python.

results*.json : Result produced by running tester.py with different server instances.