__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
sys.modules["sqlite3.dbapi2"] = sys.modules["pysqlite3.dbapi2"]

import os
import requests
import json
from datetime import datetime
from src.linkedin_copilot.crew import LinkedinCopilotCrew


class LinkedInCopilot:
    def __init__(self):
        """Initialize LinkedIn Copilot with crew configuration"""
        self.crew_config = LinkedinCopilotCrew()
    
    def post_to_linkedin(self, content, access_token):
        """Post content to LinkedIn with proper API calls"""
        try:
            # Use the correct endpoint for getting user profile
            # Try v2/userinfo first (works with openid scope)
            profile_response = requests.get(
                'https://api.linkedin.com/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                person_urn = profile_data.get('sub')  # 'sub' field contains the user ID
                
                if not person_urn:
                    return "Failed to get user ID from profile"
                    
            else:
                # Fallback: try the people endpoint with r_liteprofile scope
                profile_response = requests.get(
                    'https://api.linkedin.com/v2/people/(id:{person})',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                
                if profile_response.status_code != 200:
                    error_msg = f"Failed to fetch profile: {profile_response.status_code} - {profile_response.text}"
                    print(error_msg)
                    return error_msg
                    
                profile_data = profile_response.json()
                person_urn = profile_data.get('id')
            
            if not person_urn:
                return "Could not extract person URN from profile"
            
            # Create the post using UGC API
            post_data = {
                "author": f"urn:li:person:{person_urn}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            # Post to LinkedIn UGC API
            response = requests.post(
                'https://api.linkedin.com/v2/ugcPosts',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json',
                    'X-Restli-Protocol-Version': '2.0.0'
                },
                json=post_data
            )
            
            if response.status_code == 201:
                return True
            else:
                error_msg = f"LinkedIn API error: {response.status_code} - {response.text}"
                print(error_msg)
                return error_msg
        
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"Error posting to LinkedIn: {e}\n{tb}")
            return f"Exception: {e}"

    def get_daily_summary(self):
        """Get today's news summary"""
        try:
            crew = self.crew_config.create_summary_crew()
            result = crew.kickoff()
            return str(result)
        except Exception as e:
            return f"Error getting daily summary: {str(e)}"
    
    def generate_content(self, topic):
        """Generate LinkedIn content for given topic"""
        try:
            crew = self.crew_config.create_content_crew(topic)
            result = crew.kickoff()
            return str(result)
        except Exception as e:
            return f"Error generating content: {str(e)}"
    
    def post_to_linkedin_share_api(self, content, access_token):
        """Alternative method using LinkedIn Share API"""
        try:
            # Get user profile using the correct endpoint
            profile_response = requests.get(
                'https://api.linkedin.com/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            if profile_response.status_code != 200:
                return f"Failed to fetch profile: {profile_response.status_code} - {profile_response.text}"
                
            profile_data = profile_response.json()
            person_urn = profile_data.get('sub')
            
            if not person_urn:
                return "Could not extract person URN from profile"
            
            # Use the Share API instead
            share_data = {
                "owner": f"urn:li:person:{person_urn}",
                "text": {
                    "text": content
                },
                "visibility": {
                    "code": "anyone"
                }
            }
            
            response = requests.post(
                'https://api.linkedin.com/v2/shares',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json',
                    'X-Restli-Protocol-Version': '2.0.0'
                },
                json=share_data
            )
            
            if response.status_code == 201:
                return True
            else:
                return f"LinkedIn Share API error: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Exception in share API: {e}"
    
    def find_leads(self, access_token):
        """Find potential leads from recent engagement"""
        try:
            crew = self.crew_config.create_lead_crew()
            result = crew.kickoff()
            
            # Parse result into list
            leads = str(result).split('\n')
            return [lead.strip() for lead in leads if lead.strip()]
            
        except Exception as e:
            print(f"Error finding leads: {e}")
            return []

def run():
    print("[Entry Point] run() called. Running basic LinkedInCopilot demo...")
    copilot = LinkedInCopilot()
    print("\n--- Daily Summary ---")
    print(copilot.get_daily_summary())
    print("\n--- Example Content Generation ---")
    print(copilot.generate_content("AI in the workplace"))

def train():
    print("[Entry Point] train() called. Training functionality is not yet implemented.")

def replay():
    print("[Entry Point] replay() called. Replay functionality is not yet implemented.")

def test():
    print("[Entry Point] test() called. Test functionality is not yet implemented.")