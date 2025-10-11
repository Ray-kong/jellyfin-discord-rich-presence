# Jellyfin Discord Rich Presence
[![pypresence](https://img.shields.io/badge/using-pypresence-00bb88.svg?style=for-the-badge&logo=discord&logoWidth=20)](https://github.com/qwertyquerty/pypresence)

## Overview

This project integrates Jellyfin with Discord Rich Presence, allowing you to display your currently playing media on Jellyfin as your Discord status. The script fetches the currently playing media from Jellyfin and updates your Discord status with rich details about the media, including thumbnails, playback progress, and external links.

## Features

- **Real-time Discord Status Updates**: Displays currently playing media from [Jellyfin](https://github.com/jellyfin/jellyfin) on Discord
- **Multiple Media Type Support**:
  - **Music**: Shows track name, artists, album, and playback progress
  - **Movies**: Displays title, year, genres, and high-quality posters
  - **TV Shows**: Shows series name, season, episode number, episode title, and series artwork
- **High-Quality Thumbnails**: 
  - Direct Jellyfin thumbnail integration (800x1200 at 95% quality)
  - OMDB API fallback for movie posters
  - Series posters for TV episodes
- **Rich Playback Information**:
  - Current position and total duration
  - Playback percentage
  - Paused/muted status indicators
  - Client device information
- **External Links**: IMDb buttons in Discord presence (when available)
- **Robust Connection Management**:
  - Automatic reconnection with exponential backoff
  - Connection health checks
  - Retry mechanisms for failed updates
  - Graceful error handling
- **Beautiful CLI Interface**:
  - Colored terminal output with status indicators
  - Live connection status display
  - Real-time playback information
  - Comprehensive logging
- **Smart Activity Types**: 
  - "Watching" for movies and TV shows
  - "Listening" for music

## Prerequisites

- A running instance of Jellyfin with a valid API key
- A Discord application with the Client ID to connect to Discord RPC
- Python 3.7 or higher installed
- Discord desktop application running
- OMDB API key (optional, for enhanced movie posters)

## Installation

1. **Clone the Repository:**

    ```bash
    git clone https://github.com/Ray-kong/jellyfin-discord-rich-presence.git
    cd jellyfin-discord-rich-presence
    ```

2. **Install the Required Python Packages:**

    Use the `requirements.txt` file to install all necessary dependencies:

    ```bash
    pip install -r requirements.txt
    ```

    Required packages:
    - `pypresence` - Discord Rich Presence integration
    - `python-dotenv` - Environment variable management
    - `requests` - HTTP requests to Jellyfin API
    - `colorama` - Colored terminal output
    - `musicbrainzngs` - Music metadata fetching

3. **Create a `.env` File:**

    Create a `.env` file in the project root directory with the following environment variables:

    ```env
    JELLYFIN_URL=<Your Jellyfin server URL>
    JELLYFIN_API_KEY=<Your Jellyfin API key>
    JELLYFIN_USER_ID=<Your Jellyfin user ID>
    DISCORD_CLIENT_ID=<Your Discord application client ID>
    OMDB_API_KEY=<Your OMDB API key>  # Optional, for enhanced movie posters
    ```

    ### How to Obtain Required Values:

    - **Jellyfin API Key:**
        1. Log in to your Jellyfin server web interface
        2. Go to `Dashboard` → `API Keys`
        3. Click `+` to create a new API key
        4. Give it a name (e.g., "Discord RPC")
        5. Copy the generated API key

    - **Jellyfin User ID:**
        1. Go to `Dashboard` → `Users`
        2. Click on your username
        3. The user ID is in the browser URL: `.../users/<USER_ID>`
        4. Copy the alphanumeric ID

    - **Discord Client ID:**
        1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
        2. Click "New Application" and give it a name (e.g., "Jellyfin")
        3. Go to the "General Information" tab
        4. Copy the "Application ID" (this is your Client ID)
        5. Note: The application name will appear in your Discord status

    - **OMDB API Key (Optional):**
        1. Go to [OMDB API](http://www.omdbapi.com/apikey.aspx)
        2. Select the free tier and enter your email
        3. Verify your email and copy the API key
        4. Add it to your `.env` file for enhanced movie poster support

4. **Configure Your Discord Application (Optional):**

    - You can upload custom images to your Discord application for better branding
    - Go to your application in the Discord Developer Portal
    - Navigate to "Rich Presence" → "Art Assets"
    - Upload images with names like "jellyfin" for the default icon

## Usage

1. **Run the Script:**

    ```bash
    python main.py
    ```

2. **What to Expect:**

    - The script will display a startup banner with connection information
    - Connection status is shown with colored indicators (🟢 connected, 🔴 disconnected)
    - Currently playing media is displayed with:
      - Media title and details
      - Playback time and percentage
      - Client device information
      - Playback status (playing/paused/muted)

3. **Continuous Operation:**

    - The script updates your Discord status every 5 seconds
    - If no media is playing, the Discord status will be cleared
    - The script automatically reconnects if Discord disconnects
    - For 24/7 operation, consider running it on a server or always-on device

4. **Stopping the Script:**

    - Press `Ctrl+C` to gracefully stop the script
    - The Discord presence will be cleared automatically

## Troubleshooting

### Discord Status Not Showing

- Ensure Discord desktop application is running (not just the web version)
- Check that your Discord Client ID is correct in the `.env` file
- Verify that Discord is not in "Invisible" mode
- Try restarting both the script and Discord

### Connection Issues

- The script includes automatic reconnection with exponential backoff
- Check the `jellyfin_rpc.log` file for detailed error messages
- Ensure your Jellyfin server is accessible from your network
- Verify all environment variables are correctly set

### Thumbnails Not Showing

- For Jellyfin thumbnails: Ensure your Jellyfin server is publicly accessible or on the same network
- For OMDB posters: Verify your OMDB API key is valid and has remaining requests
- Discord may cache images, so changes might take a few minutes to appear

### Script Crashes or Errors

- Check the `jellyfin_rpc.log` file for detailed error information
- Ensure all required packages are installed: `pip install -r requirements.txt`
- Verify your Python version is 3.7 or higher: `python --version`

## Logging

- Logs are automatically saved to `jellyfin_rpc.log` in the project directory
- Log information includes:
  - Connection status and reconnection attempts
  - Currently playing media details
  - Playback status and client information
  - Error messages and stack traces
  - RPC update details
- Logs are useful for debugging issues and monitoring the script's operation

## Advanced Configuration

### Running as a Service (Linux)

Create a systemd service file at `/etc/systemd/system/jellyfin-discord-rpc.service`:

```ini
[Unit]
Description=Jellyfin Discord Rich Presence
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/jellyfin-discord-rich-presence
ExecStart=/usr/bin/python3 /path/to/jellyfin-discord-rich-presence/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then enable and start the service:

```bash
sudo systemctl enable jellyfin-discord-rpc
sudo systemctl start jellyfin-discord-rpc
```

### Running in the Background (Windows)

Use Task Scheduler to run the script at startup:

1. Open Task Scheduler
2. Create a new task
3. Set trigger to "At startup"
4. Set action to run `python.exe` with the path to `main.py`
5. Configure to run whether user is logged in or not

## Contributing

Contributions are welcome! Feel free to:

- Fork the repository
- Create a feature branch
- Make your improvements
- Submit a pull request

Please ensure your code follows the existing style and includes appropriate error handling.

## Acknowledgments

- [pypresence](https://github.com/qwertyquerty/pypresence) - Discord Rich Presence library
- [Jellyfin](https://github.com/jellyfin/jellyfin) - The Free Software Media System
- [OMDB API](http://www.omdbapi.com/) - Movie database API

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

## Support

If you encounter any issues or have questions:

1. Check the `jellyfin_rpc.log` file for error details
2. Review the Troubleshooting section above
3. Open an issue on GitHub with:
   - Your Python version
   - Relevant log excerpts
   - Steps to reproduce the issue
   - Your operating system
