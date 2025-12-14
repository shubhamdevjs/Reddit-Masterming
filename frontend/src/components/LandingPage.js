import React, { useState } from 'react';

const IconTrash = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6" />
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
    <path d="M10 11v6" />
    <path d="M14 11v6" />
    <path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" />
  </svg>
);

const ThemeBadge = ({ children }) => (
  <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-white/10 text-white border border-white/30">
    {children}
  </span>
);

const LandingPage = ({ campaigns, onCreateCampaign, onSelectCampaign, onRefreshCampaigns }) => {
  const [deleting, setDeleting] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Sample campaign (hardcoded demo)
  const sampleCampaign = {
    id: 'sample-demo',
    companyName: 'AI Edge Devices',
    companyDescription: 'Building intelligent, privacy-first solutions for edge devices. Demo campaign showing realistic Reddit campaign output.',
    postsPerWeek: 3,
    subreddits: ['r/devops', 'r/privacy', 'r/raspberry_pi', 'r/Android', 'r/apple', 'r/netsec', 'r/MachineLearning', 'r/Entrepreneur'],
    personas: [
      { persona_username: 'asdfadsf' },
      { persona_username: 'sdafasdf' }
    ],
    isSample: true
  };

  const handleDeleteCampaign = async (campaignId, campaignName) => {
    if (!window.confirm(`Are you sure you want to delete "${campaignName}"? This action cannot be undone.`)) return;
    try {
      setDeleting(campaignId);
      // Remove from localStorage
      const saved = localStorage.getItem('redditCampaigns');
      const list = saved ? JSON.parse(saved) : [];
      const updated = list.filter((c) => c.id !== campaignId);
      localStorage.setItem('redditCampaigns', JSON.stringify(updated));

      setSuccess(`Campaign "${campaignName}" deleted locally`);
      setTimeout(() => {
        setSuccess(null);
        if (onRefreshCampaigns) onRefreshCampaigns();
      }, 800);
    } catch (err) {
      setError(`Error deleting campaign locally: ${err.message}`);
      setTimeout(() => setError(null), 2000);
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-slate-50">
      <header className="max-w-6xl mx-auto px-6 pt-12 pb-10">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-3">
              <ThemeBadge>Reddit Ops</ThemeBadge>
              <ThemeBadge>Content AI</ThemeBadge>
            </div>
            <h1 className="text-4xl md:text-5xl font-black tracking-tight text-white">Campaign Control Room</h1>
            <p className="text-slate-200 text-lg mt-3 max-w-2xl">
              Launch, review, and prune Reddit campaigns with a single glance. Clean cards, fast actions, instant deletes.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onRefreshCampaigns}
              className="px-4 py-2 rounded-lg border border-white/30 text-white hover:bg-white/10 transition"
            >
              Refresh
            </button>
            <button
              onClick={onCreateCampaign}
              className="px-5 py-2.5 rounded-lg bg-amber-400 text-slate-900 font-semibold shadow-lg shadow-amber-500/20 hover:shadow-amber-500/40 transition"
            >
              + Create Campaign
            </button>
          </div>
        </div>
      </header>

      {error && (
        <div className="max-w-6xl mx-auto px-6 mb-4">
          <div className="bg-red-500/10 border border-red-400/40 rounded-lg p-4 text-red-100">
            {error}
          </div>
        </div>
      )}

      {success && (
        <div className="max-w-6xl mx-auto px-6 mb-4">
          <div className="bg-emerald-500/10 border border-emerald-400/40 rounded-lg p-4 text-emerald-100">
            {success}
          </div>
        </div>
      )}

      <div className="max-w-6xl mx-auto px-6 pb-12 space-y-4">
        {campaigns.length > 0 && (
          <div className="flex items-center gap-2 text-sm text-slate-200/80">
            <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10">Active: {campaigns.length}</span>
            <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10">Click a card to open the plan</span>
          </div>
        )}

        {/* Sample Campaign Card */}
        <div className="mb-8 pb-8 border-b border-white/10">
          <h3 className="text-sm uppercase tracking-[0.2em] text-slate-300/70 mb-4 font-semibold">Sample Campaign</h3>
          <div className="group relative overflow-hidden rounded-2xl border border-emerald-400/30 bg-emerald-500/5 backdrop-blur shadow-xl hover:-translate-y-1 transition-all duration-300">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-400/10 via-emerald-400/5 to-teal-500/10 opacity-0 group-hover:opacity-100 transition"></div>

            <div className="relative z-10 p-6 space-y-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="text-xs uppercase tracking-[0.2em] text-emerald-200/90">Campaign (Demo)</p>
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/20 text-emerald-100 border border-emerald-400/40">
                      Sample
                    </span>
                  </div>
                  <h3 className="text-xl font-semibold text-white leading-tight">{sampleCampaign.companyName}</h3>
                  <p className="text-sm text-slate-200/80 mt-1 line-clamp-2">{sampleCampaign.companyDescription}</p>
                </div>
              </div>

              <div className="flex items-center gap-2 text-xs text-slate-200/80">
                <span className="px-3 py-1 rounded-full bg-emerald-400/20 border border-emerald-400/40 font-semibold text-emerald-100">{sampleCampaign.postsPerWeek} posts/week</span>
                <span className="px-3 py-1 rounded-full bg-white/10 border border-white/15">{sampleCampaign.subreddits.length} subreddits</span>
                <span className="px-3 py-1 rounded-full bg-white/10 border border-white/15">{sampleCampaign.personas.length} personas</span>
              </div>

              <div className="pt-2">
                <button
                  onClick={() => onSelectCampaign(sampleCampaign.id)}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-500 text-white font-semibold py-2.5 shadow-md shadow-emerald-500/20 hover:shadow-emerald-500/40 transition hover:bg-emerald-600"
                >
                  View Sample Plan
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* User Campaigns */}
        {campaigns.length === 0 ? (
          <div className="bg-white/5 border border-white/10 rounded-2xl p-14 text-center shadow-2xl backdrop-blur">
            <div className="text-6xl mb-4">📊</div>
            <h2 className="text-3xl font-semibold text-white mb-2">No campaigns yet</h2>
            <p className="text-lg text-slate-200 mb-8">Create your first Reddit campaign to get started.</p>
            <button
              onClick={onCreateCampaign}
              className="px-6 py-3 rounded-lg bg-amber-400 text-slate-900 font-semibold shadow-lg shadow-amber-500/20 hover:shadow-amber-500/40 transition"
            >
              Create Campaign
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {campaigns.map((campaign) => (
              <div key={campaign.id} className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 backdrop-blur shadow-xl hover:-translate-y-1 transition-all duration-300">
                <div className="absolute inset-0 bg-gradient-to-br from-amber-400/0 via-amber-400/5 to-pink-500/10 opacity-0 group-hover:opacity-100 transition"></div>

                {deleting === campaign.id && (
                  <div className="absolute inset-0 bg-slate-900/70 backdrop-blur-sm flex items-center justify-center z-20">
                    <div className="text-center text-slate-100">
                      <div className="animate-spin inline-block w-8 h-8 border-4 border-white/30 border-t-amber-400 rounded-full mb-2"></div>
                      <p className="text-sm">Deleting...</p>
                    </div>
                  </div>
                )}

                <div className="relative z-10 p-6 space-y-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <p className="text-xs uppercase tracking-[0.2em] text-amber-200/90 mb-1">Campaign</p>
                      <h3 className="text-xl font-semibold text-white leading-tight">{campaign.companyName || campaign.companyInfo}</h3>
                      <p className="text-sm text-slate-200/80 mt-1 line-clamp-2">{campaign.companyDescription || 'Reddit growth mission'}</p>
                    </div>
                    <button
                      onClick={() => handleDeleteCampaign(campaign.id, campaign.companyName || campaign.companyInfo)}
                      disabled={deleting === campaign.id}
                      className="p-2 text-rose-200 hover:text-rose-50 hover:bg-rose-500/20 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Delete campaign"
                    >
                      <IconTrash />
                    </button>
                  </div>

                  <div className="flex items-center gap-2 text-xs text-slate-200/80">
                    <span className="px-3 py-1 rounded-full bg-white/10 border border-white/15 font-semibold text-amber-100">{campaign.postsPerWeek} posts/week</span>
                    <span className="px-3 py-1 rounded-full bg-white/5 border border-white/15">{campaign.subreddits?.length || 0} subreddits</span>
                    <span className="px-3 py-1 rounded-full bg-white/5 border border-white/15">{campaign.personas?.length || 0} personas</span>
                  </div>

                  <div className="pt-2">
                    <button
                      onClick={() => onSelectCampaign(campaign.id)}
                      disabled={deleting === campaign.id}
                      className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-white text-slate-900 font-semibold py-2.5 shadow-md shadow-amber-500/20 hover:shadow-amber-500/40 transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      View Plan
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default LandingPage;
