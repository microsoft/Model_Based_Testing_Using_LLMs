import smtpd
import asyncore

class CustomSMTPServer(smtpd.DebuggingServer):
    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        print(f"Message received from: {peer}")
        print(f"From: {mailfrom}")
        print(f"To: {rcpttos}")
        print(f"Message:\n{data.decode()}")
        return None

if __name__ == "__main__":
    server = CustomSMTPServer(('127.0.0.1', 8025), None)
    print("SMTP Debugging Server running on localhost:8025")
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        print("\nServer stopped.")
