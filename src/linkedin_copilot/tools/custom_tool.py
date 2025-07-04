import os
import requests
import json
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class LinkedInAuth:
    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id or os.getenv('LINKEDIN_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('LINKEDIN_CLIENT_SECRET')
        self.redirect_uri = "https://linkedin-copilot.streamlit.app/signin-linkedin"
        self.scope = "openid profile email w_member_social r_liteprofile w_organization_social"
        
        # LinkedIn API endpoints
        self.auth_url = "https://www.linkedin.com/oauth/v2/authorization"
        self.token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        self.profile_url = "https://api.linkedin.com/v2/userinfo"
    
    def get_auth_url(self) -> str:
        """Generate LinkedIn OAuth authorization URL"""
        if not self.client_id:
            raise ValueError("LinkedIn Client ID is required")
            
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': self.scope,
            'state': 'linkedin_auth'  # CSRF protection
        }
        
        url = f"{self.auth_url}?{urllib.parse.urlencode(params)}"
        print(f"Generated auth URL: {url}")
        return url
    
    def exchange_code_for_token(self, auth_code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token"""
        if not self.client_id or not self.client_secret:
            raise ValueError("LinkedIn Client ID and Secret are required")
        
        data = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            response = requests.post(self.token_url, data=data, headers=headers, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Store token with expiration time
            expires_in = token_data.get('expires_in', 3600)  # Default 1 hour
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            return {
                'access_token': token_data['access_token'],
                'expires_at': expires_at,
                'expires_in': expires_in,
                'token_type': token_data.get('token_type', 'Bearer')
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Failed to exchange code for token: {e}")
            return None
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Invalid response from LinkedIn token endpoint: {e}")
            return None
    
    def get_user_profile(self, access_token: str):
        """Get user profile with proper error handling"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Try userinfo endpoint first
            profile_response = requests.get(
                self.profile_url,
                headers=headers,
                timeout=10
            )
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                
                # Format the response consistently
                formatted_profile = {
                    'id': profile_data.get('sub'),
                    'firstName': {
                        'localized': {
                            'en_US': profile_data.get('given_name', 'User')
                        }
                    },
                    'lastName': {
                        'localized': {
                            'en_US': profile_data.get('family_name', '')
                        }
                    },
                    'headline': {
                        'localized': {
                            'en_US': profile_data.get('headline', 'LinkedIn User')
                        }
                    }
                }
                
                if profile_data.get('picture'):
                    formatted_profile['profilePicture'] = {
                        'displayImage~': {
                            'elements': [{
                                'identifiers': [{'identifier': profile_data['picture']}]
                            }]
                        }
                    }
                
                return {
                    'profile': formatted_profile,
                    'email': {
                        'elements': [{
                            'handle~': {
                                'emailAddress': profile_data.get('email', '')
                            }
                        }]
                    }
                }
            else:
                print(f"Profile fetch failed: {profile_response.status_code} - {profile_response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Failed to get user profile: {e}")
            return None
    
    def is_token_valid(self, token_data: Optional[Dict[str, Any]]) -> bool:
        """Check if access token is still valid"""
        if not token_data or 'expires_at' not in token_data:
            return False
        buffer_time = timedelta(minutes=5)
        return datetime.now() + buffer_time < token_data['expires_at']
    
    def refresh_token_if_needed(self, token_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not self.is_token_valid(token_data):
            print("Token has expired. Re-authentication required.")
            return None
        return token_data
    
    def revoke_token(self, access_token: str) -> bool:
        return True
    
    def get_user_display_name(self, profile_data: Dict[str, Any]) -> str:
        try:
            first_name = profile_data.get('firstName', {}).get('localized', {})
            last_name = profile_data.get('lastName', {}).get('localized', {})
            first_name_value = next(iter(first_name.values())) if first_name else 'User'
            last_name_value = next(iter(last_name.values())) if last_name else ''
            
            return f"{first_name_value} {last_name_value}".strip()
        except (AttributeError, KeyError):
            return "LinkedIn User"
    
    def get_user_email(self, email_data: Dict[str, Any]) -> Optional[str]:
        """Extract email from email data"""
        try:
            if 'elements' in email_data and email_data['elements']:
                return email_data['elements'][0]['handle~']['emailAddress']
        except (KeyError, IndexError, TypeError):
            pass
        return None
    
    def get_profile_picture_url(self, profile_data: Dict[str, Any]) -> Optional[str]:
        """Extract profile picture URL from profile data"""
        try:
            picture_data = profile_data.get('profilePicture', {})
            if 'displayImage~' in picture_data:
                elements = picture_data['displayImage~'].get('elements', [])
                if elements:
                    # Get the largest available image
                    return elements[-1]['identifiers'][0]['identifier']
        except (KeyError, IndexError, TypeError):
            pass
        return None
    
    def validate_credentials(self) -> bool:
        """Validate that required credentials are available"""
        return bool(self.client_id and self.client_secret)


class LinkedInAPIError(Exception):
    """Custom exception for LinkedIn API errors"""
    pass


class LinkedInAuthError(Exception):
    """Custom exception for LinkedIn authentication errors"""
    pass