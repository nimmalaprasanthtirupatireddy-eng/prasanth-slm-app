import React from 'react';

const Sidebar = ({ conversations, activeConv, onSelectConv, onNewChat, onLogout }) => {
  return (
    <div className="sidebar">
      <button className="new-chat-btn" onClick={onNewChat}>
        <span>+</span> New Chat
      </button>
      
      <div className="conv-list">
        {conversations.map((conv) => (
          <div 
            key={conv.id} 
            className={`conv-item ${activeConv === conv.id ? 'active' : ''}`}
            onClick={() => onSelectConv(conv.id)}
          >
            {conv.title}
          </div>
        ))}
      </div>

      <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid var(--glass-border)' }}>
        <button 
          className="conv-item" 
          onClick={onLogout}
          style={{ width: '100%', background: 'transparent', border: 'none', textAlign: 'left', color: '#ff4444' }}
        >
          Logout
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
