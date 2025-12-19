import asyncio
from aiosmtpd.controller import Controller

class CustomSMTPHandler:
    async def handle_DATA(self, server, session, envelope):
        print(f"Message from: {envelope.mail_from}")
        print(f"Message to: {envelope.rcpt_tos}")
        print(f"Message data:\n{envelope.content.decode('utf-8')}")
        return '250 OK'

# Run the SMTP server
controller = Controller(CustomSMTPHandler(), hostname='127.0.0.1', port=8025)
controller.start()
print("SMTP server is running on port 8025...")

try:
    asyncio.get_event_loop().run_forever()
except KeyboardInterrupt:
    controller.stop()
    print("SMTP server stopped.")

