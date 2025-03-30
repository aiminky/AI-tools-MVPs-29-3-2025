from agency_swarm.tools import BaseTool
from pydantic import Field
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os
from dotenv import load_dotenv
import json

load_dotenv()

API_KEY = os.getenv('YOUTUBE_API_KEY')
OAUTH_CREDENTIALS = os.getenv('YOUTUBE_OAUTH_CREDENTIALS')

class ChannelDemographicsTool(BaseTool):
    """
    A tool to fetch YouTube channel demographics and statistics including subscriber count,
    view count, video count, and other metrics. For metrics requiring OAuth (like audience demographics),
    it will use the OAuth credentials if available.
    """

    channel_id: str = Field(
        ...,
        description="The YouTube channel ID to analyze. Can be found in the channel's URL."
    )

    def run(self):
        """
        Fetches channel demographics and statistics using YouTube Data API.
        Returns the data as a formatted string.
        """
        try:
            # Check if API key is set
            if not API_KEY:
                return "Error: YouTube API key is not set."

            # Initialize the YouTube API client
            youtube = build('youtube', 'v3', developerKey=API_KEY)
            
            # Fetch basic channel statistics
            channel_response = youtube.channels().list(
                part='statistics,snippet,contentDetails',
                id=self.channel_id
            ).execute()

            # Log the API response for debugging
            print("API Response:", channel_response)

            if 'items' not in channel_response or not channel_response['items']:
                return "Channel not found or invalid channel ID."

            channel_data = channel_response['items'][0]
            stats = channel_data['statistics']
            snippet = channel_data['snippet']

            # Prepare the basic statistics
            basic_stats = {
                "Channel Name": snippet['title'],
                "Description": snippet['description'][:200] + "..." if len(snippet['description']) > 200 else snippet['description'],
                "Country": snippet.get('country', 'Not specified'),
                "Created Date": snippet['publishedAt'],
                "Subscriber Count": stats.get('subscriberCount', 'Hidden'),
                "Total Views": stats['viewCount'],
                "Total Videos": stats['videoCount'],
                "Custom URL": snippet.get('customUrl', 'Not available')
            }

            # Try to get advanced demographics if OAuth credentials are available
            advanced_stats = {}
            if OAUTH_CREDENTIALS:
                try:
                    credentials = Credentials.from_authorized_user_info(
                        json.loads(OAUTH_CREDENTIALS),
                        ['https://www.googleapis.com/auth/youtube.readonly']
                    )
                    youtube_oauth = build('youtube', 'v3', credentials=credentials)
                    
                    # Note: This is a placeholder as demographic data requires special access
                    # and is only available through YouTube Analytics API
                    advanced_stats = {
                        "Note": "Advanced demographics require YouTube Analytics API access"
                    }
                except Exception as e:
                    advanced_stats = {
                        "Error": f"Could not fetch advanced demographics: {str(e)}"
                    }

            # Format the output
            output = "Channel Demographics Report\n"
            output += "========================\n\n"
            
            output += "Basic Statistics:\n"
            output += "----------------\n"
            for key, value in basic_stats.items():
                output += f"{key}: {value}\n"
            
            if advanced_stats:
                output += "\nAdvanced Demographics:\n"
                output += "---------------------\n"
                for key, value in advanced_stats.items():
                    output += f"{key}: {value}\n"

            return output

        except Exception as e:
            return f"Error fetching channel demographics: {str(e)}"

if __name__ == "__main__":
    # Test the tool with a known channel ID (e.g., Google Developers channel)
    # UC5v4qL8vmoSH7GaPjuqRiCQ
    tool = ChannelDemographicsTool(channel_id="UCSv4qL8vmoSH7GaPjuqRiCQ")
    print(tool.run()) 