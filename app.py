import os
import pickle
import json
import base64
import re
import requests
import logging
from flask import Flask, request, jsonify
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from bs4 import BeautifulSoup

# Initialize Flask app
app = Flask(__name__)

# Setup logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Slack webhook URL (replace with your actual Slack Webhook URL)
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/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"  # Replace with your Slack webhook URL

# Gmail API Scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

# Redirect URI
REDIRECT_URI = "http://localhost:5000/oauth2callback"

# Token storage
TOKEN_FILE = "token.pickle"

# Domain to match (change this as needed)
DOMAIN_TO_MATCH = "gmail.com"


def extract_domain(email):
    """Extract the domain from an email address."""
    match = re.search(r"@([\w.-]+)", email)
    return match.group(1) if match else None


@app.route("/")
def index():
    return "Flask app is running!"


@app.route("/oauth2callback/")
def oauth2callback():
    """Handle the OAuth2 callback and exchange the authorization code for a token."""
    try:
        auth_code = request.args.get("code")
        if not auth_code:
            logger.error("Authorization code not found.")
            return jsonify({"error": "Authorization code not found"}), 400

        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        flow.redirect_uri = REDIRECT_URI
        creds = flow.fetch_token(code=auth_code)

        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

        logger.info("Authorization successful!")
        return jsonify({"message": "Authorization successful!"}), 200
    except Exception as error:
        logger.error(f"Error during OAuth2 callback: {error}")
        return jsonify({"error": str(error)}), 500


def authenticate_gmail():
    """Authenticate the Gmail API using the fixed redirect URI."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            logger.info("Credentials refreshed.")
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            flow.redirect_uri = REDIRECT_URI
            auth_url, _ = flow.authorization_url(prompt="consent")
            logger.info(f"Please go to this URL and authorize access:\n{auth_url}")
            auth_code = input("Enter the authorization code: ")
            credentials = flow.fetch_token(code=auth_code)
            creds = flow.credentials
            with open(TOKEN_FILE, "wb") as token:
                pickle.dump(creds, token)

    logger.info("Gmail authentication successful.")
    return creds


def get_email_body(message):
    """Extract the email body from the message and return it as plain text."""
    body_data = message.get("payload", {}).get("body", {}).get("data", "")

    # If no body data, check the 'parts' field (common for multipart messages)
    if not body_data:
        parts = message.get("payload", {}).get("parts", [])
        for part in parts:
            mime_type = part.get("mimeType")
            if mime_type == "text/plain":
                body_data = part.get("body", {}).get("data", "")
                break  # Stop after finding the first text/plain part
            elif mime_type == "text/html":
                body_data = part.get("body", {}).get("data", "")
                break  # Stop after finding the first text/html part

    # If body data is found, decode it
    if body_data:
        decoded_body = base64.urlsafe_b64decode(body_data).decode("utf-8")

        # Use BeautifulSoup to parse HTML and extract text
        soup = BeautifulSoup(decoded_body, "html.parser")

        # Extract the main content, you can adjust the selector based on your needs
        main_content = soup.find(
            "body"
        )  # or any specific tag that contains the main content
        if main_content:
            return main_content.get_text(separator="\n").strip()  # Return plain text
    return "No body content available."


@app.route("/webhook", methods=["POST"])
def webhook():
    """Handles incoming email notifications from Gmail and sends them to Slack."""
    try:
        # Log received data
        data = request.json
        logger.debug(f"Received data: {json.dumps(data, indent=4)}")

        message_data = data.get("message", {}).get("data")
        if message_data:
            # Decode and log Pub/Sub message
            pubsub_message = base64.urlsafe_b64decode(message_data).decode("utf-8")
            logger.debug(f"Decoded message: {pubsub_message}")

            gmail_message_id = json.loads(pubsub_message).get("message_id")
            if gmail_message_id:
                # Get the message using Gmail API
                service = build("gmail", "v1", credentials=authenticate_gmail())
                message = (
                    service.users()
                    .messages()
                    .get(userId="me", id=gmail_message_id, format="full")
                    .execute()
                )
                logger.debug(f"Gmail message: {json.dumps(message, indent=4)}")

                # Extract the email body using the updated method
                email_body = get_email_body(message)

                # Log the body for debugging
                logger.debug(f"Email body: {email_body}")

                # Send only the email body to Slack
                slack_payload = {
                    "text": email_body  # Only the email body is sent to Slack
                }
                slack_response = requests.post(SLACK_WEBHOOK_URL, json=slack_payload)
                logger.debug(
                    f"Slack response: {slack_response.status_code} - {slack_response.text}"
                )

                if slack_response.status_code == 200:
                    logger.info("Email body sent to Slack successfully.")
                    return (
                        jsonify(
                            {
                                "status": "success",
                                "message": "Email body sent to Slack!",
                            }
                        ),
                        200,
                    )
                else:
                    logger.error("Failed to send email body to Slack.")
                    return (
                        jsonify(
                            {"status": "error", "message": "Failed to send to Slack."}
                        ),
                        500,
                    )
            else:
                logger.error("Message ID not found.")
                return (
                    jsonify({"status": "error", "message": "Message ID not found."}),
                    400,
                )
        else:
            logger.error("No message data found.")
            return (
                jsonify({"status": "error", "message": "No message data found."}),
                400,
            )

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


def start_gmail_watch():
    """Set up the Gmail watch using Pub/Sub."""
    try:
        creds = authenticate_gmail()
        logger.debug(f"Credentials: {creds}")
        service = build("gmail", "v1", credentials=creds)

        # Set up the Gmail watch API to use Pub/Sub
        request = {
            "labelIds": ["INBOX"],
            "topicName": "projects/orbital-builder-424711-v7/topics/test",  # Replace with your Pub/Sub topic
        }

        response = service.users().watch(userId="me", body=request).execute()
        logger.info(f"Watch response: {json.dumps(response, indent=2)}")

    except Exception as e:
        logger.error(f"An error occurred while setting up Gmail watch: {str(e)}")


def get_latest_message_id():
    """Fetch the most recent message ID for testing."""
    try:
        service = build("gmail", "v1", credentials=authenticate_gmail())
        response = (
            service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX"], q="is:unread")
            .execute()
        )
        if "messages" in response:
            message_id = response["messages"][0]["id"]
            logger.info(f"Latest message ID: {message_id}")
            return message_id
        else:
            logger.warning("No unread messages found.")
            return None
    except Exception as e:
        logger.error(f"Error fetching latest message: {str(e)}")
        return None


def simulate_pubsub_message():
    """Simulate the Pub/Sub message manually with a real message ID."""
    message_id = get_latest_message_id()
    if message_id:
        test_message = {
            "message": {
                "data": base64.urlsafe_b64encode(
                    json.dumps({"message_id": message_id}).encode()
                ).decode()
            }
        }
        # Manually call the webhook with a real message ID
        with app.test_client() as c:
            response = c.post("/webhook", json=test_message)
            print(f"Webhook test response: {response.data}")
    else:
        logger.warning("No message ID to test with.")


if __name__ == "__main__":
    start_gmail_watch()
    simulate_pubsub_message()  # For testing
    app.run(debug=True, host="0.0.0.0", port=5000)
