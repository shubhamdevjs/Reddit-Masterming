import React, { useState } from 'react';

const CreateCampaignForm = ({ onSubmit, onCancel }) => {
  const [formData, setFormData] = useState({
    userText: '',
    companyName: '',
    companyDescription: '',
    subredditsText: '',
    personas: [
      { persona_username: '', info: '' },
      { persona_username: '', info: '' }
    ],
    postsPerWeek: 3
  });

  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const parseKeywordsTSV = (text) => {
    const lines = text.trim().split('\n').filter(l => l.trim());
    const keywords = [];
    for (const line of lines) {
      if (line.toLowerCase().includes('keyword_id') || line.toLowerCase().includes('keyword')) continue;
      const parts = line.split('\t');
      if (parts.length >= 2) {
        keywords.push({
          keyword_id: parts[0].trim(),
          keyword: parts[1].trim()
        });
      }
    }
    return keywords;
  };

  const parseSubreddits = (text) => {
    const lines = text.trim().split('\n').filter(l => l.trim());
    const subs = [];
    for (const line of lines) {
      if (line.toLowerCase().includes('subreddit')) continue;
      const cleaned = line.trim();
      // Ensure it starts with r/
      if (cleaned && !cleaned.startsWith('r/')) {
        subs.push('r/' + cleaned);
      } else if (cleaned) {
        subs.push(cleaned);
      }
    }
    return subs;
  };

  const handlePersonaChange = (index, field, value) => {
    setFormData(prev => {
      const updatedPersonas = [...prev.personas];
      updatedPersonas[index][field] = value;
      return { ...prev, personas: updatedPersonas };
    });
  };

  const addPersona = () => {
    setFormData(prev => ({
      ...prev,
      personas: [...prev.personas, { persona_username: '', info: '' }]
    }));
  };

  const removePersona = (index) => {
    setFormData(prev => ({
      ...prev,
      personas: prev.personas.filter((_, i) => i !== index)
    }));
  };

  const validateForm = () => {
    const newErrors = {};
    
    // Company name validation
    if (!formData.companyName.trim()) {
      newErrors.companyName = 'Company name required';
    }
    
    // Company description validation
    if (!formData.companyDescription.trim()) {
      newErrors.companyDescription = 'Company description required';
    }
    
    // Keywords validation
    if (!formData.userText.trim()) {
      newErrors.userText = 'Keywords (USER_TEXT) required';
    } else {
      const lines = formData.userText.trim().split('\n').filter(l => l.trim() && !l.toLowerCase().includes('keyword_id'));
      if (lines.length === 0) {
        newErrors.userText = 'At least one keyword required';
      } else {
        // Check each keyword line has ID and text
        for (const line of lines) {
          const parts = line.split('\t');
          if (parts.length < 2) {
            newErrors.userText = 'Each keyword must have format: keyword_id[TAB]keyword';
            break;
          }
          if (!parts[0].trim()) {
            newErrors.userText = 'Each keyword needs a non-empty keyword_id';
            break;
          }
          if (!parts[1].trim()) {
            newErrors.userText = `Keyword text missing for id '${parts[0].trim()}'`;
            break;
          }
        }
      }
    }
    
    // Subreddits validation
    if (!formData.subredditsText.trim()) {
      newErrors.subredditsText = 'Subreddits required';
    } else {
      const lines = formData.subredditsText.trim().split('\n').filter(l => l.trim() && !l.toLowerCase().includes('subreddit'));
      if (lines.length === 0) {
        newErrors.subredditsText = 'At least one subreddit required';
      } else {
        // Check each subreddit has r/ prefix
        for (const line of lines) {
          const cleaned = line.trim();
          if (cleaned && !cleaned.startsWith('r/')) {
            newErrors.subredditsText = `Invalid subreddit '${cleaned}'. Each subreddit must start with 'r/'`;
            break;
          }
        }
      }
    }
    
    // Personas validation - minimum 2 required
    if (formData.personas.length < 2) {
      newErrors.personas = 'At least 2 personas are required';
    } else {
      for (let i = 0; i < formData.personas.length; i++) {
        const p = formData.personas[i];
        if (!p.persona_username || !p.persona_username.trim()) {
          newErrors.personas = `Persona ${i + 1}: Username required`;
          break;
        }
        if (!p.info || !p.info.trim()) {
          newErrors.personas = `Persona ${i + 1}: Info/description required`;
          break;
        }
      }
    }
    
    // Posts per week validation
    if (formData.postsPerWeek < 1 || formData.postsPerWeek > 50) {
      newErrors.postsPerWeek = 'Posts per week must be between 1 and 50';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setProgress(0);

    // Start progress simulation (10 minutes = 600 seconds)
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        const increment = (100 / 600) * 2; // Increment every 2 seconds
        return Math.min(prev + increment, 98); // Cap at 98% until complete
      });
    }, 2000);

    try {
      if (!validateForm()) {
        clearInterval(progressInterval);
        setIsSubmitting(false);
        setProgress(0);
        return;
      }

      const keywords = parseKeywordsTSV(formData.userText);
      const subreddits = parseSubreddits(formData.subredditsText);
      const personas = formData.personas.map(p => ({
        persona_username: p.persona_username.trim(),
        info: p.info.trim()
      }));

      const requestData = {
        company_name: formData.companyName.trim(),
        company_description: formData.companyDescription.trim(),
        target_posts_per_week: parseInt(formData.postsPerWeek),
        subreddits: subreddits,
        keywords: keywords,
        personas: personas
      };

      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/campaigns/create/v2`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create campaign');
      }

      const result = await response.json();

      const campaignData = {
        companyName: result.campaign.company_name,
        companyWebsite: result.campaign.company_website,
        companyDescription: result.campaign.company_description,
        personas: result.campaign.personas,
        subreddits: result.campaign.subreddits,
        keywords: result.campaign.keywords,
        postsPerWeek: result.campaign.target_posts_per_week,
        nestedData: result.nestedData,
        companyInfo: `${result.campaign.company_name} - ${result.campaign.company_website}`,
        createdAt: new Date().toISOString(),
        id: result.campaignId || Date.now(),
        campaignId: result.campaignId,
        outputDir: result.outputDir,
      };

      clearInterval(progressInterval);
      setProgress(100);
      
      // Small delay to show 100% before closing
      setTimeout(() => {
        onSubmit(campaignData);
      }, 300);
    } catch (error) {
      console.error('Error submitting campaign:', error);
      clearInterval(progressInterval);
      setErrors({ submit: error.message });
      setProgress(0);
    } finally {
      clearInterval(progressInterval);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/75 backdrop-blur-sm">
      {/* Progress Loader Overlay */}
      {isSubmitting && (
        <div className="absolute inset-0 z-[60] flex items-center justify-center bg-slate-950/90 backdrop-blur-md">
          <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-gradient-to-br from-slate-900 to-slate-950 p-8 shadow-2xl">
            <div className="mb-6 text-center">
              <div className="mx-auto mb-4 h-16 w-16 animate-spin rounded-full border-4 border-slate-700 border-t-primary-500"></div>
              <h3 className="text-xl font-bold text-white mb-2">Generating Campaign</h3>
              <p className="text-sm text-slate-400">AI pipeline running • Estimated 5-10 minutes</p>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-slate-400">Progress</span>
                <span className="text-primary-400">{Math.round(progress)}%</span>
              </div>
              
              <div className="h-3 overflow-hidden rounded-full bg-slate-800 shadow-inner">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-primary-500 to-amber-400 shadow-lg transition-all duration-500 ease-out"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>

              <div className="space-y-1.5 pt-3 text-xs text-slate-500">
                <div className="flex items-center gap-2">
                  <div className={`h-1.5 w-1.5 rounded-full ${progress > 10 ? 'bg-green-500' : 'bg-slate-700'}`}></div>
                  <span className={progress > 10 ? 'text-slate-300' : ''}>Clustering keywords</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className={`h-1.5 w-1.5 rounded-full ${progress > 30 ? 'bg-green-500' : 'bg-slate-700'}`}></div>
                  <span className={progress > 30 ? 'text-slate-300' : ''}>Generating titles</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className={`h-1.5 w-1.5 rounded-full ${progress > 50 ? 'bg-green-500' : 'bg-slate-700'}`}></div>
                  <span className={progress > 50 ? 'text-slate-300' : ''}>Creating post bodies</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className={`h-1.5 w-1.5 rounded-full ${progress > 70 ? 'bg-green-500' : 'bg-slate-700'}`}></div>
                  <span className={progress > 70 ? 'text-slate-300' : ''}>Generating comments</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className={`h-1.5 w-1.5 rounded-full ${progress > 90 ? 'bg-green-500' : 'bg-slate-700'}`}></div>
                  <span className={progress > 90 ? 'text-slate-300' : ''}>Building calendar</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="relative w-full max-w-4xl max-h-[92vh] overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 via-slate-900/95 to-slate-950 shadow-3xl">
        <div className="pointer-events-none absolute -top-12 -right-20 h-56 w-56 rounded-full bg-primary-500/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-16 -left-24 h-64 w-64 rounded-full bg-amber-400/10 blur-3xl" />

        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-800 bg-slate-900/90 px-8 py-5 backdrop-blur-sm">
          <div>
            <p className="text-[11px] uppercase tracking-[0.2em] text-amber-300/80">Campaign Wizard</p>
            <h2 className="text-2xl font-black text-white">Create New Campaign</h2>
            <p className="text-sm text-slate-400">Structured inputs → ready-to-post Reddit calendar</p>
          </div>
          <button
            onClick={onCancel}
            className="grid h-11 w-11 place-items-center rounded-xl border border-slate-700 bg-slate-800 text-slate-200 text-2xl leading-none shadow-lg transition hover:-translate-y-0.5 hover:border-slate-600 hover:text-white hover:shadow-primary-500/30"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="relative max-h-[calc(92vh-92px)] overflow-y-auto px-8 py-6 space-y-6">
          <div className="flex items-start gap-3 rounded-xl border border-amber-300/20 bg-amber-400/5 px-4 py-3 text-amber-100">
            <div className="mt-0.5 h-2 w-2 rounded-full bg-amber-300" />
            <p className="text-sm leading-relaxed">
              <strong className="text-amber-200">Paste data as generated in the notebook.</strong> Keywords & personas as TSV (tab-separated), subreddits one per line.
            </p>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="lg:col-span-2 rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow-inner">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-400">Queries</p>
                  <h3 className="text-lg font-semibold text-white">Keywords (TSV)</h3>
                </div>
                <span className="rounded-full bg-primary-500/15 px-3 py-1 text-xs font-semibold text-primary-200 border border-primary-500/30">TSV</span>
              </div>
              <textarea
                id="userText"
                name="userText"
                value={formData.userText}
                onChange={handleInputChange}
                placeholder="keyword_id&#9;keyword&#10;K1&#9;affordable AI solutions&#10;K2&#9;AI for small business&#10;K3&#9;enterprise AI tools"
                rows="6"
                className={`w-full rounded-lg border bg-slate-950/60 px-4 py-3 font-mono text-sm text-slate-50 shadow-inner transition focus:outline-none focus:ring-2 focus:ring-primary-500/60 ${
                  errors.userText ? 'border-red-500/80 focus:ring-red-500/60' : 'border-slate-800 focus:border-primary-500/60'
                }`}
              />
              {errors.userText && <p className="mt-2 text-sm text-red-400">{errors.userText}</p>}
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow-inner">
              <p className="text-xs uppercase tracking-wide text-slate-400">Identity</p>
              <label htmlFor="companyName" className="mt-1 block text-sm font-semibold text-white">
                COMPANY_NAME <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                id="companyName"
                name="companyName"
                value={formData.companyName}
                onChange={handleInputChange}
                placeholder="AiforDevice"
                className={`mt-2 w-full rounded-lg border bg-slate-950/60 px-4 py-3 text-slate-50 shadow-inner transition focus:outline-none focus:ring-2 focus:ring-primary-500/60 ${
                  errors.companyName ? 'border-red-500/80 focus:ring-red-500/60' : 'border-slate-800 focus:border-primary-500/60'
                }`}
              />
              {errors.companyName && <p className="mt-2 text-sm text-red-400">{errors.companyName}</p>}
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow-inner">
              <p className="text-xs uppercase tracking-wide text-slate-400">Narrative</p>
              <label htmlFor="companyDescription" className="mt-1 block text-sm font-semibold text-white">
                COMPANY_DESCRIPTION <span className="text-red-400">*</span>
              </label>
              <textarea
                id="companyDescription"
                name="companyDescription"
                value={formData.companyDescription}
                onChange={handleInputChange}
                placeholder="Device-first AI platform shipping a compact LLM on every device..."
                rows="6"
                className={`mt-2 w-full rounded-lg border bg-slate-950/60 px-4 py-3 text-slate-50 shadow-inner transition focus:outline-none focus:ring-2 focus:ring-primary-500/60 ${
                  errors.companyDescription ? 'border-red-500/80 focus:ring-red-500/60' : 'border-slate-800 focus:border-primary-500/60'
                }`}
              />
              {errors.companyDescription && <p className="mt-2 text-sm text-red-400">{errors.companyDescription}</p>}
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow-inner lg:col-span-1">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-400">Channels</p>
                  <h3 className="text-lg font-semibold text-white">Subreddits</h3>
                </div>
                <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-200 border border-emerald-500/30">One per line</span>
              </div>
              <textarea
                id="subredditsText"
                name="subredditsText"
                value={formData.subredditsText}
                onChange={handleInputChange}
                placeholder="r/Entrepreneur&#10;r/startups&#10;r/SaaS&#10;r/smallbusiness&#10;r/marketing"
                rows="6"
                className={`w-full rounded-lg border bg-slate-950/60 px-4 py-3 font-mono text-sm text-slate-50 shadow-inner transition focus:outline-none focus:ring-2 focus:ring-primary-500/60 ${
                  errors.subredditsText ? 'border-red-500/80 focus:ring-red-500/60' : 'border-slate-800 focus:border-primary-500/60'
                }`}
              />
              {errors.subredditsText && <p className="mt-2 text-sm text-red-400">{errors.subredditsText}</p>}
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow-inner flex flex-col justify-between">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">Cadence</p>
                <label htmlFor="postsPerWeek" className="mt-1 block text-sm font-semibold text-white">
                  TARGET_POSTS_PER_WEEK <span className="text-red-400">*</span>
                </label>
                <input
                  type="number"
                  id="postsPerWeek"
                  name="postsPerWeek"
                  value={formData.postsPerWeek}
                  onChange={handleInputChange}
                  min="1"
                  max="50"
                  className={`mt-2 w-full rounded-lg border bg-slate-950/60 px-4 py-3 text-slate-50 shadow-inner transition focus:outline-none focus:ring-2 focus:ring-primary-500/60 ${
                    errors.postsPerWeek ? 'border-red-500/80 focus:ring-red-500/60' : 'border-slate-800 focus:border-primary-500/60'
                  }`}
                />
                {errors.postsPerWeek && <p className="mt-2 text-sm text-red-400">{errors.postsPerWeek}</p>}
              </div>
              <p className="mt-4 text-xs text-slate-400">We’ll auto-balance personas × subreddits to meet this target.</p>
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow-inner">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">Audience voices</p>
                <h3 className="text-lg font-semibold text-white">Personas (min 2)</h3>
              </div>
              <button
                type="button"
                onClick={addPersona}
                className="inline-flex items-center gap-2 rounded-lg border border-primary-500/40 bg-primary-500/15 px-4 py-2 text-sm font-semibold text-primary-100 transition hover:-translate-y-0.5 hover:border-primary-500/70 hover:bg-primary-500/25"
              >
                + Add Persona
              </button>
            </div>

            {formData.personas.map((persona, index) => (
              <div key={index} className="mb-4 rounded-lg border border-slate-800 bg-slate-950/60 p-5 shadow-inner">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Persona {index + 1}</p>
                    <h4 className="text-base font-semibold text-white">Voice & angle</h4>
                  </div>
                  {formData.personas.length > 2 && (
                    <button
                      type="button"
                      onClick={() => removePersona(index)}
                      className="text-xs font-semibold text-red-300 hover:text-red-200"
                    >
                      Remove
                    </button>
                  )}
                </div>

                <div className="mt-4 space-y-3">
                  <div>
                    <label className="block text-sm font-semibold text-slate-200 mb-1">
                      Username <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="text"
                      value={persona.persona_username}
                      onChange={(e) => handlePersonaChange(index, 'persona_username', e.target.value)}
                      placeholder="e.g., maya_edge, noah_privacy"
                      className="w-full rounded-lg border border-slate-800 bg-slate-900 px-4 py-2.5 text-slate-50 shadow-inner focus:outline-none focus:ring-2 focus:ring-primary-500/60"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-slate-200 mb-1">
                      Persona Info <span className="text-red-400">*</span>
                    </label>
                    <textarea
                      value={persona.info}
                      onChange={(e) => handlePersonaChange(index, 'info', e.target.value)}
                      placeholder="Background, role, interests, tone, objections"
                      rows="4"
                      className="w-full rounded-lg border border-slate-800 bg-slate-900 px-4 py-3 text-slate-50 shadow-inner focus:outline-none focus:ring-2 focus:ring-primary-500/60"
                    />
                  </div>
                </div>
              </div>
            ))}

            {errors.personas && <p className="mt-2 text-sm text-red-400">{errors.personas}</p>}
          </div>

          {errors.submit && (
            <div className="rounded-lg border border-red-400/40 bg-red-500/10 px-4 py-3 text-red-100">
              <p className="text-sm font-semibold">Error: {errors.submit}</p>
            </div>
          )}

          <div className="sticky bottom-0 left-0 right-0 -mx-8 -mb-6 bg-gradient-to-t from-slate-950 via-slate-950/90 to-transparent px-8 pb-4 pt-6">
            <div className="flex gap-4">
              <button
                type="button"
                onClick={onCancel}
                className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-6 py-3 font-semibold text-slate-100 transition hover:-translate-y-0.5 hover:border-slate-600 hover:bg-slate-850"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className={`flex-1 rounded-lg px-6 py-3 font-semibold shadow-lg transition hover:-translate-y-0.5 hover:shadow-primary-500/30 ${
                  isSubmitting
                    ? 'bg-slate-700 text-slate-300 cursor-not-allowed'
                    : 'bg-primary-500 text-white hover:bg-primary-600'
                }`}
              >
                {isSubmitting ? 'Creating...' : 'Create Campaign'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateCampaignForm;
