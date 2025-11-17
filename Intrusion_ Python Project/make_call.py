import os
from twilio.rest import Client

# Environment configuration
DEV_MODE = os.getenv('DEV_MODE', 'False') == "True"

# Twilio credentials
account_sid = "your_twilio_sid"
auth_token = "your_twilio_auth_token"
twilio_number = "+123456789"
to_number = "+123456789"

client = Client(account_sid, auth_token)


def start_intrusion_call():
    if DEV_MODE:
        print("DEV_MODE: call would have been initiated")
        return

    # Twilio will wait 1.5 seconds AFTER YOU ANSWER the call
    call = client.calls.create(
        to=to_number,
        from_=twilio_number,
        twiml=(
            '<Response>'
            '<Pause length="3" />'
            '<Say voice="alice">'
            'Hello. You have an intruder on your premises. Check camera one.'
            '</Say>'
            '</Response>'
        )
    )

    print(f"Call initiated. SID: {call.sid}")


if __name__ == "__main__":
    start_intrusion_call()
