import React, { useState, useEffect } from 'react';
import LandingPage from './components/LandingPage';
import CreateCampaignForm from './components/CreateCampaignForm';
import CampaignCalendar from './components/CampaignCalendar';
import sampleData from './components/reddit_output_nested.json';
import './App.css';

// Transform sample JSON data into campaign format
const SAMPLE_CAMPAIGN = {
  id: 'sample-demo',
  isSample: true,
  companyName: 'AI Edge Devices',
  companyDescription: 'Building intelligent, privacy-first solutions for edge devices. Demo campaign showing realistic Reddit campaign output.',
  companyInfo: 'AI Edge Devices - Edge AI made simple',
  postsPerWeek: 3,
  subreddits: ['r/devops', 'r/privacy', 'r/raspberry_pi', 'r/Android', 'r/apple', 'r/netsec', 'r/MachineLearning', 'r/Entrepreneur'],
  personas: [
    { persona_username: 'asdfadsf', info: 'DevOps engineer exploring edge AI solutions' },
    { persona_username: 'sdafasdf', info: 'Privacy advocate interested in local LLMs' }
  ],
  createdAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(), // 30 days ago
  nestedData: {
    posts: sampleData.posts.map((post, index) => ({
      post_id: post.post_id,
      week_number: Math.ceil((index + 1) / 2), // Roughly 2 posts per week
      subreddit: post.subreddit,
      post_title: post.title,
      post_body: post.body,
      title: post.title,
      body: post.body,
      author_username: post.author_username,
      username: post.author_username,
      timestamp: post.timestamp,
      comments: post.comments.map(comment => ({
        comment_id: comment.comment_id,
        post_id: comment.post_id,
        author_username: comment.username,
        username: comment.username,
        comment_text: comment.comment_text,
        body: comment.comment_text,
        parent_comment_id: comment.parent_comment_id || null,
        timestamp: comment.timestamp
      }))
    }))
  }
};

function App() {
  const [view, setView] = useState('landing');
  const [campaigns, setCampaigns] = useState([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState(null);

  useEffect(() => {
    const savedCampaigns = localStorage.getItem('redditCampaigns');
    if (savedCampaigns) {
      setCampaigns(JSON.parse(savedCampaigns));
    }
  }, []);

  useEffect(() => {
    if (campaigns.length > 0) {
      localStorage.setItem('redditCampaigns', JSON.stringify(campaigns));
    }
  }, [campaigns]);

  const handleCreateCampaign = () => {
    setView('create');
  };

  const handleCancelCreate = () => {
    setView('landing');
  };

  const handleSubmitCampaign = (campaignData) => {
    // Ensure campaign has unique ID and timestamp
    const newCampaign = {
      ...campaignData,
      id: campaignData.id || campaignData.campaignId || Date.now(),
      campaignId: campaignData.campaignId || Date.now(),
      createdAt: campaignData.createdAt || new Date().toISOString(),
      lastUpdated: new Date().toISOString()
    };
    setCampaigns([...campaigns, newCampaign]);
    setView('landing');
  };

  const handleSelectCampaign = (campaignId) => {
    setSelectedCampaignId(campaignId);
    setView('calendar');
  };

  const handleBackToLanding = () => {
    setSelectedCampaignId(null);
    setView('landing');
  };

  const handleRefreshCampaigns = () => {
    const savedCampaigns = localStorage.getItem('redditCampaigns');
    if (savedCampaigns) {
      setCampaigns(JSON.parse(savedCampaigns));
    }
  };

  const selectedCampaign = selectedCampaignId === 'sample-demo' 
    ? SAMPLE_CAMPAIGN 
    : campaigns.find(c => c.id === selectedCampaignId);

  return (
    <div className="App">
      {view === 'landing' && (
        <LandingPage
          campaigns={campaigns}
          onCreateCampaign={handleCreateCampaign}
          onSelectCampaign={handleSelectCampaign}
          onRefreshCampaigns={handleRefreshCampaigns}
        />
      )}

      {view === 'create' && (
        <CreateCampaignForm
          onSubmit={handleSubmitCampaign}
          onCancel={handleCancelCreate}
        />
      )}

      {view === 'calendar' && selectedCampaign && (
        <CampaignCalendar
          campaign={selectedCampaign}
          onBack={handleBackToLanding}
        />
      )}
    </div>
  );
}

export default App;
