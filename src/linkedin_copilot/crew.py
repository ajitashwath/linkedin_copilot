from crewai import Agent, Crew, Process, Task
from crewai_tools import SerperDevTool
from src.linkedin_copilot.tools.custom_tool import LinkedInAuth
import yaml
import os

class LinkedinCopilotCrew:
    """LinkedIn Copilot crew configuration"""
    
    def __init__(self):
        self.serper_tool = SerperDevTool()
        self.linkedin_auth = LinkedInAuth()
        self.agents_config = self._load_config('config/agents.yaml')
        self.tasks_config = self._load_config('config/tasks.yaml')
    
    def _load_config(self, config_path):
        """Load YAML configuration file"""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"Config file {config_path} not found. Using default configuration.")
            return {}
    
    def create_researcher(self):
        """Create content researcher agent"""
        config = self.agents_config.get('researcher', {})
        return Agent(
            role=config.get('role', 'LinkedIn Content Researcher'),
            goal=config.get('goal', 'Research trending topics and gather relevant information for LinkedIn posts'),
            backstory=config.get('backstory', 'You are an expert LinkedIn content researcher.'),
            tools=[self.serper_tool],
            verbose=True
        )
    
    def create_content_creator(self):
        """Create content creator agent"""
        config = self.agents_config.get('content_creator', {})
        return Agent(
            role=config.get('role', 'LinkedIn Content Creator'),
            goal=config.get('goal', 'Create engaging, professional LinkedIn posts that drive engagement'),
            backstory=config.get('backstory', 'You are a seasoned LinkedIn content creator.'),
            verbose=True
        )
    
    def create_lead_generator(self):
        """Create lead generation agent"""
        config = self.agents_config.get('lead_generator', {})
        return Agent(
            role=config.get('role', 'Lead Generation Specialist'),
            goal=config.get('goal', 'Identify and analyze potential leads from LinkedIn engagement'),
            backstory=config.get('backstory', 'You are a lead generation expert.'),
            #tools=[self.linkedin_auth],
            verbose=True
        )
    
    def create_news_summarizer(self):
        """Create news summarizer agent"""
        config = self.agents_config.get('news_summarizer', {})
        return Agent(
            role=config.get('role', 'Business News Summarizer'),
            goal=config.get('goal', 'Provide concise, relevant daily business news summaries'),
            backstory=config.get('backstory', 'You are a business news analyst.'),
            tools=[self.serper_tool],
            verbose=True
        )
    
    def create_research_task(self, topic, agent):
        """Create research task"""
        config = self.tasks_config.get('research_topic', {})
        # Fixed: Ensure we have a valid string for description
        base_description = config.get('description', "Research the topic '{topic}' and gather current information.")
        description = base_description.format(topic=topic if topic else "general business trends")
        
        return Task(
            description=description,
            agent=agent,
            expected_output=config.get('expected_output', 'Research summary with key insights')
        )
    
    def create_content_task(self, topic, agent):
        """Create content creation task"""
        config = self.tasks_config.get('create_content', {})
        # Fixed: Ensure we have a valid string for description
        base_description = config.get('description', "Create an engaging LinkedIn post about '{topic}'.")
        description = base_description.format(topic=topic if topic else "general business topics")
        
        return Task(
            description=description,
            agent=agent,
            expected_output=config.get('expected_output', 'Complete LinkedIn post ready to publish')
        )
    
    def create_daily_summary_task(self, agent):
        """Create daily summary task"""
        config = self.tasks_config.get('daily_summary', {})
        return Task(
            description=config.get('description', 'Research and summarize today\'s business news.'),
            agent=agent,
            expected_output=config.get('expected_output', 'Daily business news summary')
        )
    
    def create_lead_generation_task(self, agent):
        """Create lead generation task"""
        config = self.tasks_config.get('find_leads', {})
        return Task(
            description=config.get('description', 'Analyze engagement to identify potential leads.'),
            agent=agent,
            expected_output=config.get('expected_output', 'List of potential leads')
        )
    
    def create_content_crew(self, topic):
        """Create crew for content generation"""
        # Fixed: Ensure topic is not None
        safe_topic = topic if topic else "general business trends"
        
        researcher = self.create_researcher()
        content_creator = self.create_content_creator()
        
        research_task = self.create_research_task(safe_topic, researcher)
        content_task = self.create_content_task(safe_topic, content_creator)
        
        return Crew(
            agents=[researcher, content_creator],
            tasks=[research_task, content_task],
            process=Process.sequential,
            verbose=True
        )
    
    def create_summary_crew(self):
        """Create crew for daily summary"""
        news_summarizer = self.create_news_summarizer()
        summary_task = self.create_daily_summary_task(news_summarizer)
        
        return Crew(
            agents=[news_summarizer],
            tasks=[summary_task],
            process=Process.sequential,
            verbose=True
        )
    
    def create_lead_crew(self):
        """Create crew for lead generation"""
        lead_generator = self.create_lead_generator()
        lead_task = self.create_lead_generation_task(lead_generator)
        
        return Crew(
            agents=[lead_generator],
            tasks=[lead_task],
            process=Process.sequential,
            verbose=True
        )