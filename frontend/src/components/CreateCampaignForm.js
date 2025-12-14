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

    try {
      if (!validateForm()) {
        setIsSubmitting(false);
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

      onSubmit(campaignData);
    } catch (error) {
      console.error('Error submitting campaign:', error);
      setErrors({ submit: error.message });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 overflow-y-auto">
      <div className="bg-white rounded-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto shadow-2xl my-8">
        <div className="sticky top-0 bg-white border-b-2 border-gray-100 px-8 py-6 flex justify-between items-center z-10">
          <h2 className="text-2xl font-bold text-gray-800">Create New Campaign</h2>
          <button onClick={onCancel} className="text-4xl text-gray-400 hover:text-gray-600 transition-colors leading-none">
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-8 py-6 space-y-6">
          <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              <strong>Paste your data exactly as shown in the notebook format:</strong> TSV for keywords and personas, one subreddit per line.
            </p>
          </div>

          <div>
            <label htmlFor="userText" className="block text-gray-700 font-semibold mb-2">
              Queries (Keywords) <span className="text-red-500">*</span>
            </label>
            <textarea
              id="userText"
              name="userText"
              value={formData.userText}
              onChange={handleInputChange}
              placeholder="keyword_id&#9;keyword&#10;K1&#9;best on-device llm&#10;K2&#9;llm in every device"
              rows="6"
              className={`w-full px-4 py-3 border-2 rounded-lg font-mono text-sm ${
                errors.userText ? 'border-red-500' : 'border-gray-200 focus:border-primary-500'
              } focus:outline-none`}
            />
            {errors.userText && <p className="text-red-500 text-sm mt-1">{errors.userText}</p>}
          </div>

          <div>
            <label htmlFor="companyName" className="block text-gray-700 font-semibold mb-2">
              COMPANY_NAME <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="companyName"
              name="companyName"
              value={formData.companyName}
              onChange={handleInputChange}
              placeholder="AiforDevice"
              className={`w-full px-4 py-3 border-2 rounded-lg ${
                errors.companyName ? 'border-red-500' : 'border-gray-200 focus:border-primary-500'
              } focus:outline-none`}
            />
            {errors.companyName && <p className="text-red-500 text-sm mt-1">{errors.companyName}</p>}
          </div>

          <div>
            <label htmlFor="companyDescription" className="block text-gray-700 font-semibold mb-2">
              COMPANY_DESCRIPTION <span className="text-red-500">*</span>
            </label>
            <textarea
              id="companyDescription"
              name="companyDescription"
              value={formData.companyDescription}
              onChange={handleInputChange}
              placeholder="AiforDevice is a device-first AI platform that ships a compact large language model on every device..."
              rows="6"
              className={`w-full px-4 py-3 border-2 rounded-lg ${
                errors.companyDescription ? 'border-red-500' : 'border-gray-200 focus:border-primary-500'
              } focus:outline-none`}
            />
            {errors.companyDescription && <p className="text-red-500 text-sm mt-1">{errors.companyDescription}</p>}
          </div>

          <div>
            <label htmlFor="subredditsText" className="block text-gray-700 font-semibold mb-2">
              SUBREDDITS_TEXT <span className="text-red-500">*</span>
            </label>
            <textarea
              id="subredditsText"
              name="subredditsText"
              value={formData.subredditsText}
              onChange={handleInputChange}
              placeholder="subreddit&#10;r/MachineLearning&#10;r/LocalLLaMA&#10;r/artificial"
              rows="6"
              className={`w-full px-4 py-3 border-2 rounded-lg font-mono text-sm ${
                errors.subredditsText ? 'border-red-500' : 'border-gray-200 focus:border-primary-500'
              } focus:outline-none`}
            />
            {errors.subredditsText && <p className="text-red-500 text-sm mt-1">{errors.subredditsText}</p>}
          </div>

          <div>
            <div className="flex justify-between items-center mb-4">
              <label className="block text-gray-700 font-semibold">
                PERSONAS <span className="text-red-500">*</span> (Minimum 2 required)
              </label>
              <button
                type="button"
                onClick={addPersona}
                className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors font-semibold text-sm"
              >
                + Add Persona
              </button>
            </div>

            {formData.personas.map((persona, index) => (
              <div key={index} className="bg-gray-50 border-2 border-gray-200 rounded-lg p-6 mb-4">
                <div className="flex justify-between items-start mb-4">
                  <h4 className="text-lg font-semibold text-gray-700">Persona {index + 1}</h4>
                  {formData.personas.length > 2 && (
                    <button
                      type="button"
                      onClick={() => removePersona(index)}
                      className="px-3 py-1 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors font-semibold text-sm"
                    >
                      Remove
                    </button>
                  )}
                </div>

                <div className="mb-4">
                  <label className="block text-gray-700 font-semibold mb-2">
                    Username <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={persona.persona_username}
                    onChange={(e) => handlePersonaChange(index, 'persona_username', e.target.value)}
                    placeholder="e.g., maya_edge, noah_privacy"
                    className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-primary-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-gray-700 font-semibold mb-2">
                    Persona Info <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    value={persona.info}
                    onChange={(e) => handlePersonaChange(index, 'info', e.target.value)}
                    placeholder="Describe this persona: their background, role, interests, communication style, etc."
                    rows="6"
                    className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-primary-500 focus:outline-none"
                  />
                </div>
              </div>
            ))}

            {errors.personas && <p className="text-red-500 text-sm mt-2">{errors.personas}</p>}
          </div>

          <div>
            <label htmlFor="postsPerWeek" className="block text-gray-700 font-semibold mb-2">
              TARGET_POSTS_PER_WEEK <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              id="postsPerWeek"
              name="postsPerWeek"
              value={formData.postsPerWeek}
              onChange={handleInputChange}
              min="1"
              max="50"
              className={`w-full px-4 py-3 border-2 rounded-lg ${
                errors.postsPerWeek ? 'border-red-500' : 'border-gray-200 focus:border-primary-500'
              } focus:outline-none`}
            />
            {errors.postsPerWeek && <p className="text-red-500 text-sm mt-1">{errors.postsPerWeek}</p>}
          </div>

          {errors.submit && (
            <div className="bg-red-50 border-2 border-red-200 rounded-lg p-4">
              <p className="text-red-700">
                <strong>Error:</strong> {errors.submit}
              </p>
            </div>
          )}

          <div className="flex gap-4 pt-6 border-t-2 border-gray-100">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 px-6 py-3 bg-white text-gray-600 border-2 border-gray-300 rounded-lg font-semibold hover:bg-gray-50 hover:border-gray-400 transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className={`flex-1 px-6 py-3 rounded-lg font-semibold shadow-lg hover:shadow-xl transition-all ${
                isSubmitting
                  ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
                  : 'bg-primary-500 text-white hover:bg-primary-600'
              }`}
            >
              {isSubmitting ? 'Creating...' : 'Create Campaign'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateCampaignForm;
