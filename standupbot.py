import os
import re
import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from flask import Flask, request, jsonify
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

# Flask app initialization
app = Flask(__name__)

# Slack client initialization with your bot token
slack_client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])

# Google Calendar setup
SCOPES = ['https://www.googleapis.com/auth/calendar']
creds = None
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)
service = build('calendar', 'v3', credentials=creds)

def schedule_meeting(channel_id, user_id, time):
    # Implementing the scheduling logic
    event = {
        'summary': 'Standup Meeting',
        'description': f'Scheduled from Slack by <@{user_id}>',
        'start': {
            'dateTime': time,
            'timeZone': 'Your/Timezone',
        },
        'end': {
            'dateTime': (datetime.datetime.fromisoformat(time) + datetime.timedelta(minutes=30)).isoformat(),
            'timeZone': 'Your/Timezone',
        },
        'attendees': [
            # List of attendees (if available)
        ],
    }
    try:
        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Meeting scheduled: {event.get('htmlLink')}"
    except Exception as e:
        return f"Error scheduling meeting: {e}"

def extract_time(text):
    # Simple regex to find time patterns in text
    match = re.search(r'\b\d{1,2}:\d{2}\b', text)
    if match:
        return match.group()
    return None

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json
    if data["type"] == "url_verification":
        return jsonify(challenge=data["challenge"])
    
    if data["type"] == "event_callback":
        event = data["event"]
        if event["type"] == "app_mention":
            try:
                user_id = event["user"]
                channel_id = event["channel"]
                text = event["text"]

                if "schedule standup" in text:
                    time = extract_time(text)
                    if time:
                        response = schedule_meeting(channel_id, user_id, time)
                    else:
                        response = "Could not find a valid time in your message."
                else:
                    response = "Sorry, I didn't understand that."

                slack_client.chat_postMessage(channel=channel_id, text=response)
            except SlackApiError as e:
                print(f"Error: {e}")

    return "", 200

if __name__ == "__main__":
    app.run(debug=True)
