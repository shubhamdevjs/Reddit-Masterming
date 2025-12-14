import React, { useState, useEffect } from 'react';
import LandingPage from './components/LandingPage';
import CreateCampaignForm from './components/CreateCampaignForm';
import CampaignCalendar from './components/CampaignCalendar';
import './App.css';

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

  const selectedCampaign = campaigns.find(c => c.id === selectedCampaignId);

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
