import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';
import { Paperclip, Send, Trash2, Edit3, X, FileText } from 'lucide-react';
import Sidebar from './components/Sidebar';
import Auth from './components/Auth';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem('token'));
  const [messages, setMessages] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isVerifying, setIsVerifying] = useState(true);
  const [attachedFile, setAttachedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    const verifySession = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const response = await fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (response.ok) setIsLoggedIn(true);
          else localStorage.removeItem('token');
        } catch (e) {
          console.error("Session verification failed", e);
        }
      }
      setIsVerifying(false);
    };
    verifySession();

    const handleResize = () => {
      if (window.innerWidth > 768) setIsSidebarOpen(true);
      else setIsSidebarOpen(false);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (isLoggedIn) fetchConversations();
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
    if (window.innerWidth <= 768) setIsSidebarOpen(false);
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

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        body: formData
      });
      if (response.ok) {
        const data = await response.json();
        setAttachedFile(data);
      }
    } catch (error) {
      console.error('Upload error:', error);
    } finally {
      setIsUploading(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    // The backend now handles RAG retrieval from the indexed file,
    // so we don't need to send the full content in the prompt anymore!
    const userMessage = { role: 'user', content: input };
    const displayMessage = { role: 'user', content: input + (attachedFile ? ` (📎 ${attachedFile.filename})` : '') };
    
    setMessages(prev => [...prev, displayMessage]);
    setInput('');
    setAttachedFile(null);
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
          max_tokens: 1024,
          temperature: 0.7
        })
      });

      if (!response.ok) throw new Error('Failed to get response');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantContent = "";
      
      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const content = line.slice(6);
            if (content === '[DONE]') continue;
            
            assistantContent += content;
            setMessages(prev => {
              const newMessages = [...prev];
              newMessages[newMessages.length - 1].content = assistantContent;
              return newMessages;
            });
          } else if (line.startsWith('event: metadata')) {
            // Wait for next line for data
          } else if (line.startsWith('data: {"conversation_id"')) {
             const data = JSON.parse(line.slice(6));
             if (!activeConvId) {
                setActiveConvId(data.conversation_id);
                fetchConversations();
             }
          }
        }
      }
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const deleteConversation = async (id) => {
    if (!window.confirm("Delete this chat?")) return;
    try {
      const response = await fetch(`/api/conversations/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.ok) {
        if (activeConvId === id) {
          setActiveConvId(null);
          setMessages([]);
        }
        fetchConversations();
      }
    } catch (e) { console.error(e); }
  };

  const renameConversation = async (id, title) => {
    try {
      const response = await fetch(`/api/conversations/${id}`, {
        method: 'PATCH',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}` 
        },
        body: JSON.stringify({ title })
      });
      if (response.ok) fetchConversations();
    } catch (e) { console.error(e); }
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
    // Clear RAG index on new chat
    fetch('/api/rag', { 
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    }).catch(console.error);
    
    if (window.innerWidth <= 768) setIsSidebarOpen(false);
  };

  if (isVerifying) {
    return (
      <div className="auth-overlay">
        <div className="auth-card" style={{ textAlign: 'center' }}>
          <div className="typing-indicator" style={{ margin: '0 auto 1rem' }}>
            <div className="dot"></div><div className="dot"></div><div className="dot"></div>
          </div>
          <p style={{ color: 'var(--text-muted)' }}>Verifying session...</p>
        </div>
      </div>
    );
  }

  if (!isLoggedIn) return <Auth onLogin={() => setIsLoggedIn(true)} />;

  return (
    <div style={{ display: 'flex' }}>
      {isSidebarOpen && window.innerWidth <= 768 && (
        <div className="sidebar-overlay" onClick={() => setIsSidebarOpen(false)} />
      )}
      <Sidebar 
        conversations={conversations} 
        activeConv={activeConvId} 
        onSelectConv={fetchMessages}
        onNewChat={startNewChat}
        onLogout={handleLogout}
        onDelete={deleteConversation}
        onRename={renameConversation}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />
      
      <div className={`main-content app-container ${!isSidebarOpen ? 'full' : ''}`}>
        <header className="header">
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <button className="mobile-menu-btn" onClick={() => setIsSidebarOpen(!isSidebarOpen)}>☰</button>
            <div className="title-group">
              <h1>Qwen2.5 <span style={{ fontWeight: 300, color: 'var(--text-muted)' }}>Lab</span></h1>
            </div>
          </div>
          <div className="status-badge">
            <div className="status-dot"></div> Private Cloud Online
          </div>
        </header>

        <main className="chat-window">
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', marginTop: '4rem', opacity: 0.5 }}>
              <h2>Qwen2.5 Advanced Chat</h2>
              <p>Upload files or start a conversation</p>
            </div>
          )}
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.role}`}>
              <div className="markdown-content">
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code({ node, inline, className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || '');
                      return !inline && match ? (
                        <SyntaxHighlighter
                          style={vscDarkPlus}
                          language={match[1]}
                          PreTag="div"
                          {...props}
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      ) : (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      );
                    }
                  }}
                >
                  {msg.content}
                </ReactMarkdown>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </main>

        <footer className="input-container-wrapper" style={{ padding: '0 1rem 1rem' }}>
          {attachedFile && (
            <div className="file-badge">
              <FileText size={14} />
              <span>{attachedFile.filename}</span>
              <button onClick={() => setAttachedFile(null)}><X size={14} /></button>
            </div>
          )}
          <div className="input-container">
            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              onChange={handleFileUpload}
              accept=".pdf,.txt,.js,.py,.html,.css,.md"
            />
            <button className="file-upload-btn" onClick={() => fileInputRef.current?.click()} disabled={isLoading || isUploading}>
              <Paperclip size={20} />
            </button>
            <textarea
              placeholder={isUploading ? "Reading file..." : "Ask me anything..."}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())}
              rows="1"
            />
            <button className="send-button" onClick={handleSend} disabled={isLoading || !input.trim() || isUploading}>
              <Send size={20} />
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
}

export default App;
