from agency_swarm.tools import BaseTool
from pydantic import Field
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

API_KEY = os.getenv('YOUTUBE_API_KEY')

class CompetitorSearchTool(BaseTool):
    """
    A tool to search for and identify competing YouTube channels based on keywords,
    topics, or similar content. Provides detailed analysis of competitor channels.
    """

    search_query: str = Field(
        ...,
        description="Keywords or topic to search for competing channels (e.g., 'tech reviews', 'cooking tutorials')"
    )
    
    max_results: int = Field(
        10,
        description="Maximum number of competitor channels to return (default: 10, max: 50)"
    )
    
    relevance_threshold: float = Field(
        0.5,
        description="Minimum relevance score (0-1) for including a channel in results (default: 0.5)"
    )

    def run(self):
        """
        Searches for competing channels and returns detailed analysis of each channel found.
        """
        try:
            youtube = build('youtube', 'v3', developerKey=API_KEY)
            
            # Search for channels related to the query
            search_response = youtube.search().list(
                part='snippet',
                q=self.search_query,
                type='channel',
                maxResults=self.max_results,
                relevanceLanguage='en'  # Focus on English content
            ).execute()
            
            if not search_response.get('items'):
                return "No competing channels found."
            
            # Get channel IDs for detailed information
            channel_ids = [item['snippet']['channelId'] for item in search_response['items']]
            
            # Fetch detailed channel information
            channels_response = youtube.channels().list(
                part='snippet,statistics,brandingSettings,topicDetails',
                id=','.join(channel_ids)
            ).execute()
            
            competitors = []
            
            for channel in channels_response['items']:
                # Calculate a simple relevance score based on channel keywords and description
                keywords = channel['brandingSettings'].get('channel', {}).get('keywords', '').lower()
                description = channel['snippet']['description'].lower()
                search_terms = self.search_query.lower().split()
                
                relevance_score = sum(
                    (term in keywords or term in description)
                    for term in search_terms
                ) / len(search_terms)
                
                if relevance_score >= self.relevance_threshold:
                    competitor_data = {
                        'channel_name': channel['snippet']['title'],
                        'channel_id': channel['id'],
                        'description': channel['snippet']['description'][:200] + "..." 
                            if len(channel['snippet']['description']) > 200 
                            else channel['snippet']['description'],
                        'subscriber_count': int(channel['statistics'].get('subscriberCount', 0)),
                        'video_count': int(channel['statistics'].get('videoCount', 0)),
                        'view_count': int(channel['statistics'].get('viewCount', 0)),
                        'country': channel['snippet'].get('country', 'Not specified'),
                        'created_date': channel['snippet']['publishedAt'],
                        'topics': channel.get('topicDetails', {}).get('topicCategories', []),
                        'relevance_score': relevance_score,
                        'url': f"https://www.youtube.com/channel/{channel['id']}"
                    }
                    competitors.append(competitor_data)
            
            # Sort competitors by subscriber count
            competitors.sort(key=lambda x: x['subscriber_count'], reverse=True)
            
            # Format the output
            output = f"Competitor Analysis Report for '{self.search_query}'\n"
            output += "=" * 60 + "\n\n"
            
            for idx, competitor in enumerate(competitors, 1):
                output += f"{idx}. {competitor['channel_name']}\n"
                output += f"   Relevance Score: {competitor['relevance_score']:.2f}\n"
                output += f"   Subscribers: {competitor['subscriber_count']:,}\n"
                output += f"   Total Views: {competitor['view_count']:,}\n"
                output += f"   Videos: {competitor['video_count']}\n"
                output += f"   Country: {competitor['country']}\n"
                output += f"   Description: {competitor['description']}\n"
                if competitor['topics']:
                    output += "   Topics: " + ", ".join(
                        [topic.split('/')[-1].replace('_', ' ') 
                         for topic in competitor['topics'][:3]]
                    ) + "\n"
                output += f"   URL: {competitor['url']}\n"
                output += "-" * 60 + "\n"
            
            # Add summary statistics
            avg_subs = sum(c['subscriber_count'] for c in competitors) / len(competitors)
            avg_views = sum(c['view_count'] for c in competitors) / len(competitors)
            
            output += "\nSummary Statistics:\n"
            output += f"Average Subscribers: {avg_subs:,.0f}\n"
            output += f"Average Total Views: {avg_views:,.0f}\n"
            output += f"Total Competitors Found: {len(competitors)}\n"
            
            return output

        except Exception as e:
            return f"Error searching for competitors: {str(e)}"

if __name__ == "__main__":
    # Test the tool with a search query
    tool = CompetitorSearchTool(
        search_query="tech reviews",
        max_results=5,
        relevance_threshold=0.3
    )
    print(tool.run()) 