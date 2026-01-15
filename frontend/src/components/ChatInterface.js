import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './ChatInterface.css';

const API_BASE_URL = 'http://localhost:8000/api';

function ChatInterface({ fileId, filename, onQueryComplete }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Reset messages when file changes
    setMessages([{
      type: 'system',
      content: `📄 Ready to answer questions about "${filename}"`
    }]);
  }, [fileId, filename]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!input.trim() || loading) return;

    const userMessage = {
      type: 'user',
      content: input
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/query`, {
        query: input,
        file_id: fileId
      });

      const assistantMessage = {
        type: 'assistant',
        content: response.data.response,
        cached: response.data.cached,
        cache_similarity: response.data.cache_similarity,
        cached_query: response.data.cached_query,
        response_time_ms: response.data.response_time_ms
      };

      setMessages(prev => [...prev, assistantMessage]);
      onQueryComplete();

    } catch (error) {
      const errorMessage = {
        type: 'error',
        content: error.response?.data?.detail || 'Failed to get response. Please try again.'
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <h2>💬 Chat with Document</h2>
        <span className="filename">{filename}</span>
      </div>

      <div className="messages-container">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.type}`}>
            {message.type === 'user' && <div className="message-label">You</div>}
            {message.type === 'assistant' && <div className="message-label">AI Assistant</div>}
            {message.type === 'system' && <div className="message-label">System</div>}

            <div className="message-content">{message.content}</div>

            {message.type === 'assistant' && (
              <div className="message-meta">
                {message.cached ? (
                  <span className="cache-badge cache-hit">
                    ⚡ Cache HIT (similarity: {(message.cache_similarity * 100).toFixed(1)}%)
                    {message.cached_query && message.cached_query !== message.content && (
                      <div className="cached-query-info">
                        Original: "{message.cached_query}"
                      </div>
                    )}
                  </span>
                ) : (
                  <span className="cache-badge cache-miss">
                    🔄 Cache MISS (Fresh LLM call)
                  </span>
                )}
                <span className="response-time">
                  ⏱️ {message.response_time_ms.toFixed(0)}ms
                </span>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="message assistant">
            <div className="message-label">AI Assistant</div>
            <div className="message-content typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about the document..."
          disabled={loading}
          className="chat-input"
        />
        <button type="submit" disabled={loading || !input.trim()} className="send-button">
          {loading ? '⏳' : '📤'}
        </button>
      </form>
    </div>
  );
}

export default ChatInterface;
