import { useState, useRef, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Auth from './components/Auth';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem('token'));
  const [messages, setMessages] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isLoggedIn) {
      fetchConversations();
    }
  }, [isLoggedIn]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchConversations = async () => {
    try {
      const response = await fetch('/api/conversations', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.ok) {
        const data = await response.json();
        setConversations(data);
      } else if (response.status === 401) {
        handleLogout();
      }
    } catch (error) {
      console.error('Fetch error:', error);
    }
  };

  const fetchMessages = async (convId) => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/conversations/${convId}/messages`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.ok) {
        const data = await response.json();
        setMessages(data);
        setActiveConvId(convId);
      }
    } catch (error) {
      console.error('Fetch error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          messages: [...messages, userMessage],
          conversation_id: activeConvId,
          max_tokens: 512,
          temperature: 0.7
        })
      });

      if (!response.ok) throw new Error('Failed to get response');

      const data = await response.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.content }]);
      
      if (!activeConvId) {
        setActiveConvId(data.conversation_id);
        fetchConversations();
      }
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsLoggedIn(false);
    setMessages([]);
    setConversations([]);
    setActiveConvId(null);
  };

  const startNewChat = () => {
    setActiveConvId(null);
    setMessages([]);
  };

  if (!isLoggedIn) {
    return <Auth onLogin={() => setIsLoggedIn(true)} />;
  }

  return (
    <div style={{ display: 'flex' }}>
      <Sidebar 
        conversations={conversations} 
        activeConv={activeConvId} 
        onSelectConv={fetchMessages}
        onNewChat={startNewChat}
        onLogout={handleLogout}
      />
      
      <div className="main-content app-container">
        <header className="header">
          <div className="title-group">
            <h1>Qwen2.5 <span style={{ fontWeight: 300, color: 'var(--text-muted)' }}>Mobile</span></h1>
          </div>
          <div className="status-badge">
            <div className="status-dot"></div>
            Private Cloud Online
          </div>
        </header>

        <main className="chat-window">
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', marginTop: '4rem', opacity: 0.5 }}>
              <h2>What can I help with?</h2>
              <p>Start a new conversation with Qwen2.5</p>
            </div>
          )}
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.role}`}>
              {msg.content}
            </div>
          ))}
          {isLoading && (
            <div className="typing-indicator">
              <div className="dot"></div>
              <div className="dot"></div>
              <div className="dot"></div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </main>

        <footer className="input-container">
          <textarea
            placeholder="Ask me anything..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())}
            rows="1"
          />
          <button 
            className="send-button" 
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
          >
            {isLoading ? '...' : 'Send'}
          </button>
        </footer>
      </div>
    </div>
  );
}

export default App;
