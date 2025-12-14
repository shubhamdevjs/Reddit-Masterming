import React, { useState, useEffect, useMemo, useCallback } from 'react';

const CampaignCalendar = ({ campaign, onBack }) => {
  const [posts, setPosts] = useState([]);
  const [currentWeek, setCurrentWeek] = useState(1);
  const [totalWeeks, setTotalWeeks] = useState(1);

  const copyToClipboard = async (text) => {
    if (!text) return;
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.setAttribute('readonly', '');
        textarea.style.position = 'absolute';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
    } catch (err) {
      console.error('Copy failed', err);
    }
  };

  const safeDate = useCallback((ts) => {
    if (!ts) return null;
    const d = new Date(ts);
    return Number.isNaN(d.getTime()) ? null : d;
  }, []);


  const getWeekFromTimestamp = useCallback(
    (timestamp, sortedPostsArray) => {
      if (!timestamp || !sortedPostsArray?.length) return 1;

      const postDate = safeDate(timestamp);
      const firstPostDate = safeDate(sortedPostsArray[0]?.timestamp);

      if (!postDate || !firstPostDate) return 1;

      const timeDiff = postDate.getTime() - firstPostDate.getTime();
      const daysDiff = Math.floor(timeDiff / (1000 * 60 * 60 * 24));

      return Math.floor(daysDiff / 7) + 1;
    },
    [safeDate]
  );


  useEffect(() => {
    let postsData = campaign?.nestedData?.posts || campaign?.plan?.posts || [];
    postsData = Array.isArray(postsData) ? postsData : [];

    const sorted = [...postsData].sort((a, b) => {
      const ad = safeDate(a?.timestamp)?.getTime() ?? 0;
      const bd = safeDate(b?.timestamp)?.getTime() ?? 0;
      return ad - bd;
    });

    setPosts(sorted);

    if (sorted.length) {
      const weeks = new Set();
      sorted.forEach((post) => weeks.add(getWeekFromTimestamp(post.timestamp, sorted)));
      setTotalWeeks(Math.max(...weeks, 1));
    } else {
      setTotalWeeks(1);
    }
  }, [campaign, safeDate, getWeekFromTimestamp]);

  const filteredPosts = posts.filter(
    (post) => getWeekFromTimestamp(post.timestamp, posts) === currentWeek
  );

  const sortedPosts = useMemo(() => {
    return [...filteredPosts].sort((a, b) => {
      const ad = safeDate(a?.timestamp)?.getTime() ?? 0;
      const bd = safeDate(b?.timestamp)?.getTime() ?? 0;
      return ad - bd;
    });
  }, [filteredPosts,safeDate]);

  const formatDate = (timestamp) => {
    const d = safeDate(timestamp);
    if (!d) return 'date unknown';
    return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  };

  const formatTime = (timestamp) => {
    const d = safeDate(timestamp);
    if (!d) return 'time unknown';
    return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  };

  const renderCommentThread = (comments = [], parentId = null, depth = 0) => {
    const norm = (v) => {
      if (v === null || typeof v === 'undefined') return null;
      const s = String(v).trim();
      return s.length ? s : null;
    };

    const normalizedParent = norm(parentId);

    const directComments = comments
      .filter((c) => norm(c?.parent_comment_id) === normalizedParent)
      .sort((a, b) => {
        const ad = safeDate(a?.timestamp)?.getTime() ?? 0;
        const bd = safeDate(b?.timestamp)?.getTime() ?? 0;
        return ad - bd;
      });

    return directComments.map((comment, idx) => {
      const author = comment.author_username || comment.username || 'unknown';
      const text = comment.body || comment.comment_text || '';
      const id = comment.comment_id || `${normalizedParent || 'root'}-${idx}`;

      return (
        <div key={id} className="py-3" style={{ marginLeft: `${depth * 16}px` }}>
          <div className="flex gap-3">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-gradient-to-br from-green-400 to-green-600 rounded-full flex items-center justify-center text-white font-bold text-xs">
                {author.charAt(0).toUpperCase()}
              </div>
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="font-semibold text-gray-900">u/{author}</span>

                <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
                  {comment.timestamp ? formatDate(comment.timestamp) : 'date unknown'}
                </span>

                <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
                  {comment.timestamp ? formatTime(comment.timestamp) : 'time unknown'}
                </span>

                {comment.comment_id && (
                  <span className="text-gray-400">id: {comment.comment_id}</span>
                )}

                {comment.parent_comment_id && (
                  <span className="text-gray-400">parent: {comment.parent_comment_id}</span>
                )}
              </div>

              <p className="text-sm text-gray-800 mt-1 break-words">{text}</p>

              <div className="flex gap-2 mt-2 text-xs text-gray-500">
                <button className="hover:text-blue-500 transition">Reply</button>
                <button className="hover:text-blue-500 transition">Share</button>
                <button
                  onClick={() => copyToClipboard(text)}
                  className="text-blue-600 hover:text-blue-800"
                >
                  Copy
                </button>
              </div>

              {/* children must be rendered INSIDE the comment block */}
              <div className="mt-2 border-l border-gray-200 pl-3">
                {renderCommentThread(comments, comment.comment_id ?? null, depth + 1)}
              </div>
            </div>
          </div>
        </div>
      );
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-3xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <button onClick={onBack} className="text-gray-600 hover:text-gray-900 font-semibold transition">
              ← Back
            </button>
            <div>
              <h1 className="text-xl font-bold text-gray-900">{campaign.companyName}</h1>
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-600">
              Posts: <strong>{campaign.postsPerWeek}/week</strong>
            </p>
            <p className="text-xs text-gray-500">Week {currentWeek} of {totalWeeks}</p>
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-6">
        <div className="flex gap-2 mb-6 bg-white rounded-lg p-3 border border-gray-200">
          <div className="flex items-center gap-4">
            <div className="flex gap-2">
              {Array.from({ length: totalWeeks }, (_, i) => i + 1).map((week) => (
                <button
                  key={week}
                  onClick={() => setCurrentWeek(week)}
                  className={`px-4 py-2 rounded-full font-semibold text-sm transition ${
                    currentWeek === week ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  Week {week}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          {sortedPosts.length === 0 ? (
            <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
              <p className="text-gray-600">No posts scheduled for Week {currentWeek}</p>
            </div>
          ) : (
            sortedPosts.map((post, idx) => (
              <div key={post.post_id || idx} className="bg-white rounded-lg border border-gray-200 overflow-hidden hover:border-gray-400 transition">
                <div className="p-4 border-b border-gray-200">
                  <div className="flex gap-3">
                    <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-blue-400 to-blue-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
                      {post.author_username?.charAt(0).toUpperCase()}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-sm text-gray-900">u/{post.author_username}</span>

                        <span className="px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 text-xs border border-purple-100">
                          r/{post.subreddit}
                        </span>

                        <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 text-xs">
                          {formatDate(post.timestamp)}
                        </span>

                        <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 text-xs">
                          {formatTime(post.timestamp)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="px-4 py-3">
                  <div className="flex items-start gap-2">
                    <h2 className="flex-1 text-base font-semibold text-gray-900 mb-2 hover:text-blue-600 cursor-pointer">
                      {post.title}
                    </h2>
                    <button
                      onClick={() => copyToClipboard(post.title)}
                      className="text-xs text-blue-600 hover:text-blue-800 bg-blue-50 px-2 py-1 rounded"
                    >
                      Copy title
                    </button>
                  </div>

                  <div className="flex items-start gap-2 mb-3">
                    <p className="flex-1 text-sm text-gray-700 leading-relaxed">{post.body}</p>
                    <button
                      onClick={() => copyToClipboard(post.body)}
                      className="text-xs text-blue-600 hover:text-blue-800 bg-blue-50 px-2 py-1 rounded"
                    >
                      Copy body
                    </button>
                  </div>

                  <div className="flex flex-wrap gap-2 mb-3">
                    <div className="bg-white px-3 py-2 rounded border border-gray-200">
                      <span className="text-xs text-gray-500">ID</span>
                      <div className="text-sm text-gray-900">{post.post_id}</div>
                    </div>
                    <div className="bg-blue-100 text-blue-700 px-2 py-1 rounded font-mono text-xs">
                      <strong>Keywords:</strong> {post.keyword_ids}
                    </div>
                  </div>
                </div>

                {Array.isArray(post.comments) && post.comments.length > 0 ? (
                  <div className="px-4 py-4 bg-gray-50 border-t border-gray-200">
                    <div className="flex flex-wrap items-center gap-2 mb-3 text-sm text-gray-900">
                      <span className="font-semibold">Comments ({post.comments.length})</span>
                      <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 text-xs">
                        {formatDate(post.timestamp)}
                      </span>
                      <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 text-xs">
                        {formatTime(post.timestamp)}
                      </span>
                    </div>

                    <div className="space-y-2">
                      {renderCommentThread(post.comments, null, 0)}
                    </div>
                  </div>
                ) : (
                  <div className="px-6 py-4 text-center text-gray-500">No comments scheduled for this post</div>
                )}
              </div>
            ))
          )}
        </div>

        <div className="mt-8 p-4 bg-white rounded-lg border border-gray-200 text-center text-sm text-gray-600">
          <p>Showing <strong>{sortedPosts.length}</strong> posts for Week {currentWeek}</p>
        </div>
      </div>
    </div>
  );
};

export default CampaignCalendar;
