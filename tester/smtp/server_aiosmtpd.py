import time
from aiosmtpd.controller import Controller

class CustomSMTPHandler:
    async def handle_DATA(self, server, session, envelope):
        mail_from = envelope.mail_from
        rcpt_tos = envelope.rcpt_tos
        try:
            message_text = envelope.content.decode('utf-8', errors='replace')
        except Exception:
            # fallback: ensure we never crash on unexpected content
            message_text = envelope.content.decode('latin-1', errors='replace')

        print(f"Message from: {mail_from}")
        print(f"Message to: {rcpt_tos}")
        print("Message data:\n" + message_text)

        # Return a 250 response string
        return '250 Message accepted for delivery'

if __name__ == "__main__":
    port_num = 8034
    controller = Controller(CustomSMTPHandler(), hostname='127.0.0.1', port=port_num)
    controller.start()
    print(f"SMTP server is running on 127.0.0.1:{port_num} (press Ctrl+C to stop)")

    try:
        # Simple blocking wait — avoids starting a second asyncio loop
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        controller.stop()
        print("SMTP server stopped.")
