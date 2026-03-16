import React, { useState } from 'react';
import { Plus, LogOut, Send, Trash2, Edit3, Check, X, MessageSquare } from 'lucide-react';

const Sidebar = ({ conversations, activeConv, onSelectConv, onNewChat, onLogout, onRename, onDelete, isOpen, onClose }) => {
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  const handleEditStart = (e, conv) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const handleEditSave = (e, id) => {
    e.stopPropagation();
    onRename(id, editTitle);
    setEditingId(null);
  };

  const handleEditCancel = (e) => {
    e.stopPropagation();
    setEditingId(null);
  };

  return (
    <div className={`sidebar ${!isOpen ? 'closed' : ''}`}>
      <button className="sidebar-close-btn" onClick={onClose}>&times;</button>
      
      <button className="new-chat-btn" onClick={() => { onNewChat(); onClose(); }}>
        <Plus size={18} style={{ marginRight: '8px' }} /> New Chat
      </button>
      
      <div className="conv-list">
        {conversations.map((conv) => (
          <div 
            key={conv.id} 
            className={`conv-item ${activeConv === conv.id ? 'active' : ''}`}
            onClick={() => { onSelectConv(conv.id); onClose(); }}
          >
            {editingId === conv.id ? (
              <div className="edit-container" onClick={e => e.stopPropagation()} style={{ display: 'flex', alignItems: 'center', width: '100%', gap: '4px' }}>
                <input 
                  autoFocus
                  className="edit-input"
                  value={editTitle}
                  onChange={e => setEditTitle(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleEditSave(e, conv.id)}
                  style={{ flex: 1, background: 'rgba(255,255,255,0.1)', border: '1px solid var(--accent)', borderRadius: '4px', color: 'white', padding: '2px 4px' }}
                />
                <button className="action-btn" onClick={e => handleEditSave(e, conv.id)}><Check size={14} /></button>
                <button className="action-btn" onClick={handleEditCancel}><X size={14} /></button>
              </div>
            ) : (
              <>
                <div className="conv-title">
                  <MessageSquare size={14} style={{ marginRight: '8px', opacity: 0.7 }} />
                  {conv.title}
                </div>
                <div className="conv-actions">
                  <button className="action-btn" onClick={(e) => handleEditStart(e, conv)}>
                    <Edit3 size={14} />
                  </button>
                  <button className="action-btn delete" onClick={(e) => { e.stopPropagation(); onDelete(conv.id); }}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
      
      <div className="sidebar-footer" style={{ marginTop: 'auto', padding: '1rem', borderTop: '1px solid var(--glass-border)' }}>
        <button onClick={onLogout} className="logout-btn" style={{ 
          width: '100%', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          gap: '8px',
          background: 'rgba(255, 77, 77, 0.1)',
          border: '1px solid rgba(255, 77, 77, 0.2)',
          color: '#ff4d4d',
          padding: '0.75rem',
          borderRadius: '0.75rem',
          cursor: 'pointer',
          transition: 'all 0.2s'
        }}>
          <LogOut size={18} /> Logout
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
