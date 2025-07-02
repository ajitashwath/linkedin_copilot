import os
import sys
import streamlit as st
from dotenv import load_dotenv
from src.linkedin_copilot.main import LinkedInCopilot
import requests
import json

project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="LinkedIn Copilot",
    page_icon="🔗",
    layout="wide"
)

def init_session_state():
    if 'linkedin_copilot' not in st.session_state:
        st.session_state.linkedin_copilot = None
    if 'access_token' not in st.session_state:
        st.session_state.access_token = None
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = None
    if 'generated_content' not in st.session_state:
        st.session_state.generated_content = None

def authenticate_linkedin():
    """Handle LinkedIn OAuth authentication"""
    client_id = os.getenv('LINKEDIN_CLIENT_ID')
    redirect_uri = "http://localhost:8501"  # Streamlit default
    
    auth_url = f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope=r_liteprofile%20r_emailaddress%20w_member_social"
    
    st.markdown(f"[🔗 Authenticate with LinkedIn]({auth_url})")
    
    # Handle the callback
    query_params = st.experimental_get_query_params()
    if 'code' in query_params:
        auth_code = query_params['code'][0]
        # Exchange code for access token
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        data = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': os.getenv('LINKEDIN_CLIENT_SECRET')
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            token_data = response.json()
            st.session_state.access_token = token_data['access_token']
            st.success("Successfully authenticated with LinkedIn!")
        else:
            st.error("Failed to authenticate with LinkedIn")

def get_user_profile(access_token):
    """Get user profile from LinkedIn"""
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get('https://api.linkedin.com/v2/people/~', headers=headers)
    
    if response.status_code == 200:
        return response.json()
    return None

def main():
    init_session_state()
    
    st.title("🔗 LinkedIn Copilot")
    st.markdown("Automate your LinkedIn content creation and lead generation")
    
    # Sidebar for API Keys
    with st.sidebar:
        st.header("🔑 API Configuration")
        
        openai_key = st.text_input("OpenAI API Key", type="password", help="Enter your OpenAI API key")
        serper_key = st.text_input("Serper API Key", type="password", help="Enter your Serper API key")
        linkedin_client_id = st.text_input("LinkedIn Client ID", help="Enter your LinkedIn Client ID")
        linkedin_client_secret = st.text_input("LinkedIn Client Secret", type="password", help="Enter your LinkedIn Client Secret")
        
        if st.button("Save API Keys"):
            if openai_key and serper_key and linkedin_client_id and linkedin_client_secret:
                os.environ['OPENAI_API_KEY'] = openai_key
                os.environ['SERPER_API_KEY'] = serper_key
                os.environ['LINKEDIN_CLIENT_ID'] = linkedin_client_id
                os.environ['LINKEDIN_CLIENT_SECRET'] = linkedin_client_secret
                st.success("API keys saved successfully!")
            else:
                st.error("Please fill in all API keys")
    
    # Main content
    if not st.session_state.access_token:
        st.header("🔐 LinkedIn Authentication")
        st.markdown("Please authenticate with LinkedIn to continue:")
        
        if st.button("Authenticate with LinkedIn"):
            authenticate_linkedin()
    else:
        # Initialize LinkedIn Copilot
        if not st.session_state.linkedin_copilot:
            st.session_state.linkedin_copilot = LinkedInCopilot()
        
        # Get user profile
        if not st.session_state.user_profile:
            st.session_state.user_profile = get_user_profile(st.session_state.access_token)
        
        if st.session_state.user_profile:
            st.success(f"✅ Authenticated as: {st.session_state.user_profile.get('localizedFirstName', 'User')}")
        
        # Content Generation Section
        st.header("📝 Content Generation")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            topic = st.text_input("Enter topic for LinkedIn post:", placeholder="e.g., AI trends, remote work, leadership")
            
            if st.button("Generate Content", type="primary"):
                if topic:
                    with st.spinner("Generating content..."):
                        try:
                            content = st.session_state.linkedin_copilot.generate_content(topic)
                            st.session_state.generated_content = content
                            st.success("Content generated successfully!")
                        except Exception as e:
                            st.error(f"Error generating content: {str(e)}")
                else:
                    st.error("Please enter a topic")
        
        with col2:
            if st.button("Get Today's Summary"):
                with st.spinner("Fetching today's news..."):
                    try:
                        summary = st.session_state.linkedin_copilot.get_daily_summary()
                        st.info(f"📰 Today's Summary:\n{summary}")
                    except Exception as e:
                        st.error(f"Error fetching summary: {str(e)}")
        
        # Display generated content
        if st.session_state.generated_content:
            st.subheader("Generated Content")
            st.text_area("Content to post:", value=st.session_state.generated_content, height=200, key="content_display")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📤 Post to LinkedIn", type="primary"):
                    with st.spinner("Posting to LinkedIn..."):
                        try:
                            result = st.session_state.linkedin_copilot.post_to_linkedin(
                                st.session_state.generated_content,
                                st.session_state.access_token
                            )
                            if result:
                                st.success("✅ Posted successfully to LinkedIn!")
                                st.balloons()
                            else:
                                st.error("Failed to post to LinkedIn")
                        except Exception as e:
                            st.error(f"Error posting: {str(e)}")
            
            with col2:
                if st.button("🎯 Find Leads"):
                    with st.spinner("Finding leads from engagement..."):
                        try:
                            leads = st.session_state.linkedin_copilot.find_leads(
                                st.session_state.access_token
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