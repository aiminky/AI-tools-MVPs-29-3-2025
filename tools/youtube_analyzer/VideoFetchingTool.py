from agency_swarm.tools import BaseTool
from pydantic import Field
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd

load_dotenv()

API_KEY = os.getenv('YOUTUBE_API_KEY')

class VideoFetchingTool(BaseTool):
    """
    A tool to retrieve videos from a YouTube channel with various sorting options.
    Can sort by views, date, or other metrics and return detailed information about each video.
    """

    channel_id: str = Field(
        ...,
        description="The YouTube channel ID to fetch videos from"
    )
    
    max_results: int = Field(
        50,
        description="Maximum number of videos to fetch (default: 50, max: 50)"
    )
    
    sort_by: str = Field(
        "date",
        description="Sort videos by: 'date' (newest first) or 'views' (most viewed first)"
    )

    def run(self):
        """
        Fetches videos from the specified channel and returns them sorted according to the specified criteria.
        """
        try:
            youtube = build('youtube', 'v3', developerKey=API_KEY)
            
            # First, get the upload playlist ID for the channel
            channel_response = youtube.channels().list(
                part='contentDetails',
                id=self.channel_id
            ).execute()
            
            # Log the channel response for debugging
            print("Channel Response:", channel_response)

            # Check if the channel exists
            if channel_response['pageInfo']['totalResults'] == 0:
                return f"Error: Channel not found for ID '{self.channel_id}'. Please check the channel ID."

            uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Fetch videos from the uploads playlist
            videos = []
            next_page_token = None
            
            while len(videos) < self.max_results:
                playlist_response = youtube.playlistItems().list(
                    part='snippet',
                    playlistId=uploads_playlist_id,
                    maxResults=min(50, self.max_results - len(videos)),
                    pageToken=next_page_token
                ).execute()
                
                # Log the playlist response for debugging
                print("Playlist Response:", playlist_response)

                if 'items' not in playlist_response:
                    return "No videos found in the uploads playlist."

                # Get video IDs for batch request
                video_ids = [item['snippet']['resourceId']['videoId'] 
                           for item in playlist_response['items']]
                
                # Get detailed video statistics
                video_response = youtube.videos().list(
                    part='statistics,snippet',
                    id=','.join(video_ids)
                ).execute()
                
                # Log the video response for debugging
                print("Video Response:", video_response)

                # Process each video
                for video in video_response['items']:
                    video_data = {
                        'title': video['snippet']['title'],
                        'video_id': video['id'],
                        'published_at': datetime.strptime(
                            video['snippet']['publishedAt'], 
                            '%Y-%m-%dT%H:%M:%SZ'
                        ),
                        'view_count': int(video['statistics'].get('viewCount', 0)),
                        'like_count': int(video['statistics'].get('likeCount', 0)),
                        'comment_count': int(video['statistics'].get('commentCount', 0)),
                        'url': f"https://www.youtube.com/watch?v={video['id']}"
                    }
                    videos.append(video_data)
                
                next_page_token = playlist_response.get('nextPageToken')
                if not next_page_token:
                    break
            
            # Convert to DataFrame for easier sorting and formatting
            df = pd.DataFrame(videos)
            
            # Sort based on user preference
            if self.sort_by.lower() == 'views':
                df = df.sort_values('view_count', ascending=False)
            else:  # default to date
                df = df.sort_values('published_at', ascending=False)
            
            # Format the output
            output = f"Videos from channel (sorted by {self.sort_by}):\n"
            output += "=" * 50 + "\n\n"
            
            for idx, row in df.iterrows():
                output += f"{idx + 1}. {row['title']}\n"
                output += f"   Published: {row['published_at'].strftime('%Y-%m-%d')}\n"
                output += f"   Views: {row['view_count']:,}\n"
                output += f"   Likes: {row['like_count']:,}\n"
                output += f"   Comments: {row['comment_count']:,}\n"
                output += f"   URL: {row['url']}\n"
                output += "-" * 50 + "\n"
            
            return output

        except Exception as e:
            return f"Error fetching videos: {str(e)}"

if __name__ == "__main__":
    # Test the tool with a known channel ID (e.g., Google Developers channel)
    tool = VideoFetchingTool(
        channel_id="UCSv4qL8vmoSH7GaPjuqRiCQ",
        max_results=5,
        sort_by="views"
    )
    print(tool.run())