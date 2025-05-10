# Chantbot - Anonymous Discord Posting Bot

A Discord bot that allows users to post messages anonymously to a designated channel.
All submissions are logged for moderator review, including the original author.

## Features

*   **Anonymous Posting:** Users DM the bot, and their messages (text and images) are posted by the bot to a public channel.
*   **Confirmation Step:** Users are asked to confirm before their message is posted.
*   **Moderator Logging:** All original messages, including the author's identity, content, and attachments, are logged to a private moderator channel.
*   **Image Support:** Handles image attachments alongside text.
*   *(Future: AI-powered message rephrasing option)*

## Setup & Installation

### Prerequisites

*   Python 3.8+
*   A Discord Bot Token with the "Message Content" Privileged Intent enabled.
*   Channel IDs for your anonymous posting channel and moderator log channel.

### Local Setup / For Development

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/marbel89/chantbot.git
    cd chantbot
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # Activate it:
    # Windows: .\venv\Scripts\activate
    # macOS/Linux: source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the root of the project directory (`chantbot/`) with the following content, replacing the placeholders with your actual values:
    ```env
    DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN
    ANONYMOUS_CHANNEL_ID=YOUR_ANONYMOUS_CHANNEL_ID
    MOD_LOG_CHANNEL_ID=YOUR_MOD_LOG_CHANNEL_ID
    ```
    **Important:** Ensure your `.env` file is listed in your `.gitignore` file to prevent committing secrets.

5.  **Run the bot:**
    ```bash
    python bot.py
    ```

### Hosting 

To keep the bot online permanently, you'll need to host it on a server or a hosting platform. (Todo: AWS maybe)


## Usage

1.  Invite the bot to your Discord server. Ensure it has permissions to:
    *   Read Messages
    *   Send Messages
    *   Embed Links
    *   Attach Files
    *   View Channels (in the anonymous and log channels)
2.  Users can initiate an anonymous post by sending a Direct Message (DM) to the bot.
3.  The bot will reply with options to "Post Anonymously" or "Cancel".
4.  If confirmed, the message is posted to the `ANONYMOUS_CHANNEL_ID`.
5.  The submission details are logged to the `MOD_LOG_CHANNEL_ID`.

## License

*This project is licensed under the MIT License - see the LICENSE file for details.*
