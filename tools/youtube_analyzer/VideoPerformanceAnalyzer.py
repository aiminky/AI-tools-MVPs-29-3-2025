from agency_swarm.tools import BaseTool
from pydantic import Field
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

load_dotenv()

API_KEY = os.getenv('YOUTUBE_API_KEY')

class VideoPerformanceAnalyzer(BaseTool):
    """
    A tool to analyze video performance metrics and engagement, including views,
    likes, comments, and top comments analysis. Provides detailed insights and trends.
    """

    video_id: str = Field(
        ...,
        description="The YouTube video ID to analyze"
    )
    
    include_comments: bool = Field(
        True,
        description="Whether to include top comments analysis (default: True)"
    )

    def run(self):
        """
        Analyzes video performance and returns detailed metrics and insights.
        """
        try:
            youtube = build('youtube', 'v3', developerKey=API_KEY)
            
            # Fetch video details
            video_response = youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=self.video_id
            ).execute()
            
            if not video_response['items']:
                return "Video not found."
            
            video = video_response['items'][0]
            
            # Parse video duration
            duration = video['contentDetails']['duration']
            duration = duration.replace('PT', '')
            hours = minutes = seconds = 0
            if 'H' in duration:
                hours = int(duration.split('H')[0])
                duration = duration.split('H')[1]
            if 'M' in duration:
                minutes = int(duration.split('M')[0])
                duration = duration.split('M')[1]
            if 'S' in duration:
                seconds = int(duration.split('S')[0])
            
            total_seconds = hours * 3600 + minutes * 60 + seconds
            
            # Calculate engagement metrics
            views = int(video['statistics'].get('viewCount', 0))
            likes = int(video['statistics'].get('likeCount', 0))
            comments = int(video['statistics'].get('commentCount', 0))
            
            engagement_rate = (likes + comments) / views if views > 0 else 0
            
            # Calculate time-based metrics
            published_at = datetime.strptime(
                video['snippet']['publishedAt'],
                '%Y-%m-%dT%H:%M:%SZ'
            )
            days_since_published = (datetime.utcnow() - published_at).days
            views_per_day = views / max(days_since_published, 1)
            
            # Format the main output
            output = "Video Performance Analysis\n"
            output += "=" * 50 + "\n\n"
            
            output += "Basic Information:\n"
            output += f"Title: {video['snippet']['title']}\n"
            output += f"Channel: {video['snippet']['channelTitle']}\n"
            output += f"Published: {published_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
            output += f"Duration: {hours}h {minutes}m {seconds}s\n"
            output += "-" * 50 + "\n\n"
            
            output += "Performance Metrics:\n"
            output += f"Views: {views:,}\n"
            output += f"Likes: {likes:,}\n"
            output += f"Comments: {comments:,}\n"
            output += f"Views per Day: {views_per_day:,.2f}\n"
            output += f"Engagement Rate: {engagement_rate:.2%}\n"
            output += "-" * 50 + "\n\n"
            
            # Fetch and analyze top comments if requested
            if self.include_comments and comments > 0:
                comments_response = youtube.commentThreads().list(
                    part='snippet',
                    videoId=self.video_id,
                    order='relevance',
                    maxResults=100  # Fetch more to ensure we get good samples
                ).execute()
                
                if comments_response.get('items'):
                    comment_data = []
                    
                    for item in comments_response['items']:
                        comment = item['snippet']['topLevelComment']['snippet']
                        comment_data.append({
                            'text': comment['textDisplay'],
                            'likes': comment['likeCount'],
                            'author': comment['authorDisplayName'],
                            'published_at': datetime.strptime(
                                comment['publishedAt'],
                                '%Y-%m-%dT%H:%M:%SZ'
                            )
                        })
                    
                    # Sort by likes and get top 5
                    comment_data.sort(key=lambda x: x['likes'], reverse=True)
                    top_comments = comment_data[:5]
                    
                    output += "Top Comments Analysis:\n"
                    for idx, comment in enumerate(top_comments, 1):
                        output += f"{idx}. Likes: {comment['likes']:,}\n"
                        output += f"   Author: {comment['author']}\n"
                        output += f"   Comment: {comment['text'][:200]}...\n"
                        output += f"   Posted: {comment['published_at'].strftime('%Y-%m-%d')}\n"
                        output += "\n"
                    
                    # Calculate comment sentiment distribution (simple version)
                    recent_comments = [c for c in comment_data 
                                     if (datetime.utcnow() - c['published_at']).days <= 30]
                    avg_likes_per_comment = np.mean([c['likes'] for c in recent_comments]) if recent_comments else 0
                    
                    output += "Comment Engagement Metrics:\n"
                    output += f"Average Likes per Comment: {avg_likes_per_comment:.2f}\n"
                    output += f"Recent Comments (30 days): {len(recent_comments)}\n"
            
            return output

        except Exception as e:
            return f"Error analyzing video performance: {str(e)}"

if __name__ == "__main__":
    # Test the tool with a known video ID
    tool = VideoPerformanceAnalyzer(
        video_id="jmeGqDu4tPU",  # Famous video ID for testing
        include_comments=True
    )
    print(tool.run()) 