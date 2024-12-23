Gmail to Slack Integration

This project integrates Gmail with Slack. It listens for incoming Gmail messages and sends their content (email body) to a Slack channel. The script uses Flask to serve as a webhook, the Gmail API to fetch the emails, and Slack's incoming webhook to post messages.

Prerequisites

Before running this script, make sure you have the following:

- Python 3.x
- A Google Cloud project with the Gmail API enabled.
- Slack incoming webhook URL.
- Required Python packages (listed below).

Setup

1. Install dependencies:

   Ensure you have pip installed. Then, install the required Python packages:

   pip install -r requirements.txt

   The requirements.txt should include the following libraries:

   Flask
   google-auth
   google-auth-oauthlib
   google-auth-httplib2
   google-api-python-client
   requests
   beautifulsoup4

2. Google API Credentials:

   - Go to the Google Cloud Console: https://console.cloud.google.com/.
   - Create a new project (or use an existing one).
   - Enable the Gmail API.
   - Create OAuth 2.0 credentials and download the credentials.json file.
   - Place the credentials.json file in the root directory of the project.

3. Slack Incoming Webhook:

   - Go to your Slack App settings: https://api.slack.com/messaging/webhooks.
   - Create an Incoming Webhook for your Slack workspace and channel.
   - Copy the Webhook URL and replace the SLACK_WEBHOOK_URL variable in the script with your own.

4. Running the Application:

   After setting up the required credentials and configurations, run the script:

   python app.py

   This will start the Flask server on http://localhost:5000.

OAuth2 Authentication Flow

The script uses OAuth2 for authentication. On the first run, it will prompt you to authenticate with Google.

1. Navigate to http://localhost:5000/oauth2callback to start the OAuth2 flow.
2. Follow the link to authenticate your Google account and allow access to Gmail.
3. The script will store the token in the token.pickle file for future authentication.

Webhook and Email Notification

The script listens for incoming email notifications through Google Pub/Sub. When an email is received, it:

1. Decodes the Pub/Sub message to get the message ID.
2. Fetches the email using the Gmail API.
3. Extracts the email body.
4. Sends the email body to Slack using the incoming webhook.

To test the system, you can simulate the Pub/Sub message by running the simulate_pubsub_message() function. It fetches the latest unread email (if any) and sends it to Slack.

Configuration

Token File:
- token.pickle: Stores the authenticated Gmail credentials. It is automatically created after the first OAuth2 authentication.

Environment Variables:
- SLACK_WEBHOOK_URL: Set this to your actual Slack Incoming Webhook URL.
- DOMAIN_TO_MATCH: You can set this variable to match a specific domain for email filtering (e.g., "gmail.com").

Functions

authenticate_gmail()
Authenticates the Gmail API using OAuth2. If credentials exist and are valid, it uses them. Otherwise, it triggers the OAuth2 flow to authenticate the user.

get_email_body(message)
Extracts the email body from a Gmail message. It handles both plain text and multipart emails.

/oauth2callback/
Handles the OAuth2 callback and exchanges the authorization code for a token. This route should be visited during the initial authentication.

/webhook
The main webhook that receives email notifications via Google Pub/Sub. It extracts the message ID, retrieves the email body, and sends it to Slack.

start_gmail_watch()
Sets up Gmail to watch for new emails using Google Pub/Sub. It triggers the /webhook endpoint when new emails are received.

get_latest_message_id()
Fetches the most recent unread message from Gmail (for testing purposes).

simulate_pubsub_message()
Simulates a Pub/Sub message by fetching the latest unread email and calling the /webhook endpoint manually.

Testing

You can manually simulate receiving a message from Gmail by calling the simulate_pubsub_message() function. This will fetch the latest unread message and send the email body to Slack.

Troubleshooting

- OAuth2 Issues: If you encounter issues with OAuth2 authentication, ensure that the credentials.json file is correctly placed and that you have enabled the Gmail API for your project in the Google Cloud Console.
- Slack Issues: If the email body isn't appearing in Slack, check that the Slack Webhook URL is correct and that your Slack channel is configured to accept incoming messages.
- Email Not Found: The script fetches unread emails. If no unread emails are found, ensure that your inbox has unread messages.


