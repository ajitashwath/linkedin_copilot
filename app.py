import os
import sys
import streamlit as st
from dotenv import load_dotenv
import requests
import json
import urllib.parse
from datetime import datetime, timedelta

# Add src to path BEFORE importing custom modules
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="LinkedIn Copilot",
    layout="wide"
)

class LinkedInAuth:
    """Handle LinkedIn OAuth authentication - standalone class"""
    
    def __init__(self):
        self.client_id = os.getenv('LINKEDIN_CLIENT_ID')
        self.client_secret = os.getenv('LINKEDIN_CLIENT_SECRET')
        self.redirect_uri = "http://localhost:8501"
        self.scope = "r_liteprofile r_emailaddress w_member_social"
        
    def get_auth_url(self):
        """Generate LinkedIn OAuth authorization URL"""
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': self.scope,
            'state': 'linkedin_auth'  # CSRF protection
        }
        
        base_url = "https://www.linkedin.com/oauth/v2/authorization"
        return f"{base_url}?{urllib.parse.urlencode(params)}"
    
    def exchange_code_for_token(self, auth_code):
        """Exchange authorization code for access token"""
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        
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
            response = requests.post(token_url, data=data, headers=headers)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Store token with expiration time
            expires_in = token_data.get('expires_in', 3600)  # Default 1 hour
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            return {
                'access_token': token_data['access_token'],
                'expires_at': expires_at,
                'token_type': token_data.get('token_type', 'Bearer')
            }
            
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to exchange code for token: {e}")
            return None
        except json.JSONDecodeError:
            st.error("Invalid response from LinkedIn token endpoint")
            return None
    
    def get_user_profile(self, access_token):
        """Get user profile from LinkedIn API"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Get basic profile
            profile_response = requests.get(
                'https://api.linkedin.com/v2/people/~?projection=(id,firstName,lastName,headline,profilePicture(displayImage~:playableStreams))',
                headers=headers
            )
            profile_response.raise_for_status()
            profile_data = profile_response.json()
            
            # Get email address
            email_response = requests.get(
                'https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))',
                headers=headers
            )
            
            email_data = {}
            if email_response.status_code == 200:
                email_data = email_response.json()
            
            return {
                'profile': profile_data,
                'email': email_data
            }
            
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to get user profile: {e}")
            return None
    
    def is_token_valid(self, token_data):
        """Check if access token is still valid"""
        if not token_data or 'expires_at' not in token_data:
            return False
        
        return datetime.now() < token_data['expires_at']

class LinkedInCopilotApp:
    """Main application class that handles the LinkedIn Copilot functionality"""
    
    def __init__(self):
        self.linkedin_copilot = None
        
    def lazy_load_copilot(self):
        """Lazy load the LinkedIn Copilot to avoid circular imports"""
        if self.linkedin_copilot is None:
            try:
                # Import only when needed to avoid circular imports
                from linkedin_copilot.main import LinkedInCopilot
                self.linkedin_copilot = LinkedInCopilot()
            except ImportError as e:
                st.error(f"Failed to import LinkedInCopilot: {e}")
                return None
        return self.linkedin_copilot
    
    def get_daily_summary(self):
        """Get today's news summary"""
        copilot = self.lazy_load_copilot()
        if copilot:
            return copilot.get_daily_summary()
        return "Failed to load LinkedIn Copilot"
    
    def generate_content(self, topic):
        """Generate LinkedIn content for given topic"""
        copilot = self.lazy_load_copilot()
        if copilot:
            return copilot.generate_content(topic)
        return "Failed to load LinkedIn Copilot"
    
    def post_to_linkedin(self, content, access_token):
        """Post content to LinkedIn"""
        copilot = self.lazy_load_copilot()
        if copilot:
            return copilot.post_to_linkedin(content, access_token)
        return False
    
    def find_leads(self, access_token):
        """Find potential leads from recent engagement"""
        copilot = self.lazy_load_copilot()
        if copilot:
            return copilot.find_leads(access_token)
        return []

def init_session_state():
    """Initialize session state variables"""
    if 'linkedin_copilot_app' not in st.session_state:
        st.session_state.linkedin_copilot_app = LinkedInCopilotApp()
    if 'linkedin_auth' not in st.session_state:
        st.session_state.linkedin_auth = LinkedInAuth()
    if 'token_data' not in st.session_state:
        st.session_state.token_data = None
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = None
    if 'generated_content' not in st.session_state:
        st.session_state.generated_content = None

def handle_oauth_callback():
    """Handle OAuth callback from LinkedIn"""
    # Use the new query_params method
    query_params = st.query_params
    
    if 'code' in query_params:
        auth_code = query_params['code']
        state = query_params.get('state')
        
        # Verify state parameter for CSRF protection
        if state != 'linkedin_auth':
            st.error("Invalid state parameter. Possible CSRF attack.")
            return False
        
        # Exchange code for token
        with st.spinner("Exchanging authorization code for access token..."):
            token_data = st.session_state.linkedin_auth.exchange_code_for_token(auth_code)
            
            if token_data:
                st.session_state.token_data = token_data
                
                # Get user profile
                user_profile = st.session_state.linkedin_auth.get_user_profile(
                    token_data['access_token']
                )
                
                if user_profile:
                    st.session_state.user_profile = user_profile
                    st.success("Successfully authenticated with LinkedIn!")
                    
                    # Clear query parameters to prevent re-processing
                    st.query_params.clear()
                    st.rerun()
                    return True
                else:
                    st.error("Failed to retrieve user profile")
            else:
                st.error("Failed to authenticate with LinkedIn")
    
    elif 'error' in query_params:
        error = query_params['error']
        error_description = query_params.get('error_description', 'Unknown error')
        st.error(f"LinkedIn authentication error: {error} - {error_description}")
    
    return False

def display_user_info():
    """Display authenticated user information"""
    if st.session_state.user_profile:
        profile = st.session_state.user_profile['profile']
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            # Display profile picture if available
            if 'profilePicture' in profile:
                picture_data = profile['profilePicture']
                if 'displayImage~' in picture_data:
                    elements = picture_data['displayImage~'].get('elements', [])
                    if elements:
                        # Get the largest available image
                        image_url = elements[-1]['identifiers'][0]['identifier']
                        st.image(image_url, width=100)
        
        with col2:
            first_name = profile.get('firstName', {}).get('localized', {})
            last_name = profile.get('lastName', {}).get('localized', {})
            
            # Get the first available localized name
            first_name_value = next(iter(first_name.values())) if first_name else 'User'
            last_name_value = next(iter(last_name.values())) if last_name else ''
            
            full_name = f"{first_name_value} {last_name_value}".strip()
            headline = profile.get('headline', {}).get('localized', {})
            headline_value = next(iter(headline.values())) if headline else 'LinkedIn User'
            
            st.markdown(f"**{full_name}**")
            st.markdown(f"*{headline_value}*")
            
            # Display email if available
            email_data = st.session_state.user_profile.get('email', {})
            if 'elements' in email_data and email_data['elements']:
                email = email_data['elements'][0]['handle~']['emailAddress']
                st.markdown(f"📧 {email}")
        
        # Token expiration info
        if st.session_state.token_data and 'expires_at' in st.session_state.token_data:
            expires_at = st.session_state.token_data['expires_at']
            time_left = expires_at - datetime.now()
            
            if time_left.total_seconds() > 0:
                hours_left = int(time_left.total_seconds() // 3600)
                minutes_left = int((time_left.total_seconds() % 3600) // 60)
                st.info(f"🕒 Token expires in {hours_left}h {minutes_left}m")
            else:
                st.warning("⚠️ Token has expired. Please re-authenticate.")
                if st.button("Re-authenticate"):
                    st.session_state.token_data = None
                    st.session_state.user_profile = None
                    st.rerun()

def main():
    init_session_state()
    
    st.title("🔗 LinkedIn Copilot")
    st.markdown("Automate your LinkedIn content creation and lead generation")
    
    # Handle OAuth callback
    handle_oauth_callback()
    
    # Sidebar for API Keys
    with st.sidebar:
        st.header("🔑 API Configuration")
        
        # LinkedIn API Configuration
        st.subheader("LinkedIn API")
        linkedin_client_id = st.text_input(
            "LinkedIn Client ID", 
            value=os.getenv('LINKEDIN_CLIENT_ID', ''),
            help="Enter your LinkedIn Client ID"
        )
        linkedin_client_secret = st.text_input(
            "LinkedIn Client Secret", 
            type="password",
            value=os.getenv('LINKEDIN_CLIENT_SECRET', ''),
            help="Enter your LinkedIn Client Secret"
        )
        
        # Other API Keys
        st.subheader("Other APIs")
        openai_key = st.text_input(
            "OpenAI API Key", 
            type="password",
            value=os.getenv('OPENAI_API_KEY', ''),
            help="Enter your OpenAI API key"
        )
        serper_key = st.text_input(
            "Serper API Key", 
            type="password",
            value=os.getenv('SERPER_API_KEY', ''),
            help="Enter your Serper API key"
        )
        
        if st.button("💾 Save API Keys"):
            if linkedin_client_id and linkedin_client_secret:
                os.environ['LINKEDIN_CLIENT_ID'] = linkedin_client_id
                os.environ['LINKEDIN_CLIENT_SECRET'] = linkedin_client_secret
                
                # Update the auth instance
                st.session_state.linkedin_auth.client_id = linkedin_client_id
                st.session_state.linkedin_auth.client_secret = linkedin_client_secret
                
                if openai_key:
                    os.environ['OPENAI_API_KEY'] = openai_key
                if serper_key:
                    os.environ['SERPER_API_KEY'] = serper_key
                
                st.success("✅ API keys saved successfully!")
            else:
                st.error("❌ Please provide at least LinkedIn Client ID and Secret")
        
        # Authentication status
        st.header("🔐 Authentication Status")
        if (st.session_state.token_data and 
            st.session_state.linkedin_auth.is_token_valid(st.session_state.token_data)):
            st.success("✅ Authenticated")
            if st.button("🚪 Logout"):
                st.session_state.token_data = None
                st.session_state.user_profile = None
                st.session_state.linkedin_copilot_app = LinkedInCopilotApp()  # Reset copilot
                st.rerun()
        else:
            st.error("❌ Not authenticated")
    
    # Main content
    if (not st.session_state.token_data or 
        not st.session_state.linkedin_auth.is_token_valid(st.session_state.token_data)):
        
        st.header("🔐 LinkedIn Authentication Required")
        
        if not st.session_state.linkedin_auth.client_id:
            st.warning("⚠️ Please configure your LinkedIn API credentials in the sidebar first.")
        else:
            st.markdown("Please authenticate with LinkedIn to access all features:")
            
            auth_url = st.session_state.linkedin_auth.get_auth_url()
            
            # Create a prominent authentication button
            st.markdown(f"""
            <div style="text-align: center; margin: 2rem 0;">
                <a href="{auth_url}" target="_self" style="
                    display: inline-block;
                    background-color: #0077B5;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 16px;
                ">
                    🔗 Authenticate with LinkedIn
                </a>
            </div>
            """, unsafe_allow_html=True)
            
            # Instructions
            with st.expander("📋 Authentication Instructions"):
                st.markdown("""
                1. Click the "Authenticate with LinkedIn" button above
                2. You'll be redirected to LinkedIn's authorization page
                3. Log in to your LinkedIn account if prompted
                4. Grant the requested permissions to the application
                5. You'll be redirected back to this application
                6. The authentication will be completed automatically
                
                **Required Permissions:**
                - `r_liteprofile`: Read your basic profile information
                - `r_emailaddress`: Read your email address
                - `w_member_social`: Post content on your behalf
                """)
    
    else:
        # User is authenticated - show main application
        display_user_info()
        
        st.divider()
        
        # Content Generation Section
        st.header("📝 Content Generation")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            topic = st.text_input(
                "Enter topic for LinkedIn post:", 
                placeholder="e.g., AI trends, remote work, leadership"
            )
            
            if st.button("🚀 Generate Content", type="primary"):
                if topic:
                    with st.spinner("Generating content..."):
                        try:
                            content = st.session_state.linkedin_copilot_app.generate_content(topic)
                            st.session_state.generated_content = content
                            st.success("Content generated successfully!")
                        except Exception as e:
                            st.error(f"Error generating content: {str(e)}")
                else:
                    st.error("Please enter a topic")
        
        with col2:
            if st.button("📰 Get Today's Summary"):
                with st.spinner("Fetching today's news..."):
                    try:
                        summary = st.session_state.linkedin_copilot_app.get_daily_summary()
                        st.info(f"📰 Today's Summary:\n{summary}")
                    except Exception as e:
                        st.error(f"Error fetching summary: {str(e)}")
        
        # Display generated content
        if st.session_state.generated_content:
            st.subheader("Generated Content")
            
            # Editable content area
            edited_content = st.text_area(
                "Content to post:", 
                value=st.session_state.generated_content, 
                height=200,
                key="content_editor",
                help="You can edit the generated content before posting"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📤 Post to LinkedIn", type="primary"):
                    with st.spinner("Posting to LinkedIn..."):
                        try:
                            result = st.session_state.linkedin_copilot_app.post_to_linkedin(
                                edited_content,
                                st.session_state.token_data['access_token']
                            )
                            if result:
                                st.success("✅ Posted successfully to LinkedIn!")
                                st.balloons()
                            else:
                                st.error("❌ Failed to post to LinkedIn")
                        except Exception as e:
                            st.error(f"Error posting: {str(e)}")
            
            with col2:
                if st.button("🎯 Find Leads"):
                    with st.spinner("Finding leads from engagement..."):
                        try:
                            leads = st.session_state.linkedin_copilot_app.find_leads(
                                st.session_state.token_data['access_token']
                            )
                            if leads:
                                st.subheader("🎯 Potential Leads")
                                for lead in leads:
                                    st.write(f"• {lead}")
                            else:
                                st.info("No leads found yet. Try again after some engagement.")
                        except Exception as e:
                            st.error(f"Error finding leads: {str(e)}")

if __name__ == "__main__":
    main()