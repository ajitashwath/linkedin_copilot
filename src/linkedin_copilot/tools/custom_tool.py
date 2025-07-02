import os
import requests
import json
from crewai.tools import BaseTool

class LinkedInTool(BaseTool):
    name: str = "LinkedIn API Tool"
    description: str = "Tool to interact with LinkedIn API for profile data, posts, and engagement analysis"
    
    def _run(self, action: str, access_token: str, **kwargs) -> str:
        """Execute LinkedIn API operations"""
        
        if not access_token:
            return "Error: Access token required for LinkedIn operations"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            if action == "get_profile":
                return self._get_profile(headers)
            elif action == "get_posts":
                return self._get_posts(headers)
            elif action == "get_connections":
                return self._get_connections(headers)
            elif action == "analyze_engagement":
                return self._analyze_engagement(headers, kwargs.get('post_id'))
            else:
                return f"Unknown action: {action}"
                
        except Exception as e:
            return f"Error executing LinkedIn API call: {str(e)}"
    
    def _get_profile(self, headers):
        """Get user profile information"""
        response = requests.get(
            'https://api.linkedin.com/v2/people/~?projection=(id,firstName,lastName,headline,industry,positions)',
            headers=headers
        )
        
        if response.status_code == 200:
            return json.dumps(response.json(), indent=2)
        else:
            return f"Error getting profile: {response.status_code}"
    
    def _get_posts(self, headers):
        """Get user's recent posts"""
        response = requests.get(
            'https://api.linkedin.com/v2/shares?q=owners&owners=urn:li:person:{id}&sortBy=CREATED&count=10',
            headers=headers
        )
        
        if response.status_code == 200:
            return json.dumps(response.json(), indent=2)
        else:
            return f"Error getting posts: {response.status_code}"
    
    def _get_connections(self, headers):
        """Get user connections (limited by LinkedIn API)"""
        response = requests.get(
            'https://api.linkedin.com/v2/people/~/connections?count=50',
            headers=headers
        )
        
        if response.status_code == 200:
            return json.dumps(response.json(), indent=2)
        else:
            return f"Error getting connections: {response.status_code}"
    
    def _analyze_engagement(self, headers, post_id):
        """Analyze engagement on a specific post"""
        if not post_id:
            return "Error: Post ID required for engagement analysis"
        
        # Get post likes
        likes_response = requests.get(
            f'https://api.linkedin.com/v2/socialActions/{post_id}/likes',
            headers=headers
        )
        
        # Get post comments
        comments_response = requests.get(
            f'https://api.linkedin.com/v2/socialActions/{post_id}/comments',
            headers=headers
        )
        
        engagement_data = {
            'likes': likes_response.json() if likes_response.status_code == 200 else {},
            'comments': comments_response.json() if comments_response.status_code == 200 else {}
        }
        
        return json.dumps(engagement_data, indent=2)