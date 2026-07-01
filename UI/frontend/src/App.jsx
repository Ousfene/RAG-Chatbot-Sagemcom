// src/App.jsx
import { useEffect, useRef, useState } from "react";
import "./App.css";
import botAvatar from "./assets/bot-de-discussion.png";
import userAvatar from "./assets/utilisateur.png";
import logo from "./assets/logo-sagemcom-new-charte-header.png";
import bot from "./assets/bot.png";
import { useAuth } from "./AuthContext";
import Login from "./login";

function App() {
  const { isAuthenticated, user, logout } = useAuth();

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sourcesHtml, setSourcesHtml] = useState("");
  const [isBotTyping, setIsBotTyping] = useState(false);

  const [sourcesOpen, setSourcesOpen] = useState(false); // collapsed by default

  // Animation state for chat container
  const [isChatEntering, setIsChatEntering] = useState(false);
  const [isChatLeaving, setIsChatLeaving] = useState(false);
  const ANIM_MS = 420; // must match CSS duration for enter/leave animations

  const chatEndRef = useRef(null);
  const inputRef = useRef(null);
  const SHOW_DELAY_MS = 500;

  // When authentication becomes true, play the chat "enter" animation
  useEffect(() => {
    if (isAuthenticated) {
      setIsChatEntering(true);
      const t = setTimeout(() => setIsChatEntering(false), ANIM_MS + 30);
      return () => clearTimeout(t);
    }
  }, [isAuthenticated]);

  // logout handler that plays a leave animation then actually logs out
  const handleLogout = () => {
    setIsChatLeaving(true);
    setTimeout(() => {
      setIsChatLeaving(false);
      logout();
    }, ANIM_MS + 10);
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: "user", content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsBotTyping(true);

    // hide/clear previous sources immediately (they live below input now)
    setSourcesOpen(false);
    setSourcesHtml("");

    try {
      const res = await fetch("http://127.0.0.1:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: userMessage.content,
          history: messages
            .filter(m => m.role === "user" || m.role === "assistant")
            .map(m => [m.role === "user" ? m.content : "", m.role === "assistant" ? m.content : ""])
            .filter(([u, a]) => u || a)
        })
      });
      const data = await res.json();
      const botMessage = { role: "assistant", content: data.answer };

      // append assistant message
      setMessages(prev => [...prev, botMessage]);

      // set sources after a small delay so message animation leads
      setTimeout(() => {
        setSourcesHtml(data.sources_html || "");
      }, SHOW_DELAY_MS);

    } catch (err) {
      console.error(err);
    } finally {
      setIsBotTyping(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") sendMessage();
  };

  // auto-scroll to bottom of messages (chatEndRef remains end of chat)
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isBotTyping]);

  // focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // keep caret at end after bot finishes
  useEffect(() => {
    if (!isBotTyping) {
      const t = setTimeout(() => {
        const el = inputRef.current;
        if (el) {
          el.focus();
          const len = el.value.length;
          try { el.setSelectionRange(len, len); } catch (err) {}
        }
      }, 60);
      return () => clearTimeout(t);
    }
  }, [isBotTyping]);

  if (!isAuthenticated) {
    return <Login />;
  }

  const handleClear = () => {
    setMessages([]);
    setSourcesHtml("");
    setSourcesOpen(false);
  };

  // toggle handler for sources title
  const toggleSources = () => {
    // only toggle if there are sources
    if (!sourcesHtml) return;
    setSourcesOpen(open => !open);
  };

  return (
    <div className="app">
      <img src={logo} alt="Sagemcom Logo" className="logo" />
      <button
        className="logout-arrow"
        onClick={handleLogout}
        aria-label="Se déconnecter"
        title="Se déconnecter"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <polyline points="15 18 9 12 15 6"></polyline>
          <line x1="21" y1="12" x2="9" y2="12"></line>
        </svg>
      </button>

      <div className="welcome-text">
        Bienvenue sur Sagemcom Qualité Chatbot
        <img src={bot} alt="icon" className="welcome-icon" />
      </div>

      {/* apply enter/leave classes to the chat-wrapper */}
      <div className={`chat-wrapper ${isChatEntering ? "enter" : ""} ${isChatLeaving ? "leave" : ""}`}>
        <div className="chat-container">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`chat-message ${msg.role} chat-animate`}
              style={{ animationDelay: `${idx * 60}ms` }}
            >
              {msg.role === "assistant" && (
                <span className="avatar-container">
                  <img src={botAvatar} alt="avatar" className="avatar" />
                </span>
              )}
              <div className="message-text">{msg.content}</div>
              {msg.role === "user" && (
                <span className="avatar-container">
                  <img src={userAvatar} alt="avatar" className="avatar" />
                </span>
              )}
            </div>
          ))}

          {isBotTyping && (
            <div className="chat-message assistant chat-animate">
              <span className="avatar-container">
                <img src={botAvatar} alt="avatar" className="avatar" />
              </span>
              <div className="message-text">
                <span className="typing-indicator">
                  <span className="dot" />
                  <span className="dot" />
                  <span className="dot" />
                </span>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        <button className="clear-btn" onClick={handleClear} title="Clear chat">✕</button>
      </div>

      {/* input area (unchanged) */}
      <div className="input-container" role="form" aria-label="Chat input">
        <input
          ref={inputRef}
          aria-label="Saisissez votre question"
          type="text"
          placeholder="Saisissez votre question..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyPress}
          disabled={isBotTyping}
        />
        <button
          id="send-button"
          onClick={sendMessage}
          aria-label="Envoyer"
          disabled={isBotTyping}
        >
          ➤
        </button>
      </div>

      {/* — sources panel below the input — */}
      <div className="sources-wrapper" aria-live="polite">
        <div
          role="button"
          tabIndex={0}
          className={`sources-toggle ${sourcesHtml ? "has-sources" : "no-sources"}`}
          onClick={toggleSources}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") toggleSources(); }}
          aria-expanded={sourcesOpen}
          aria-disabled={!sourcesHtml}
          title={sourcesHtml ? "Afficher / Masquer les sources" : ""}
        >
          <span className="sources-toggle-title">🔍 Sources consultées :</span>
          <span className={`sources-caret ${sourcesOpen ? "open" : ""}`}>▾</span>
        </div>

        <div
          className={`sources-panel ${sourcesOpen ? "open" : "closed"}`}
          dangerouslySetInnerHTML={{ __html: sourcesHtml || "" }}
        />
      </div>
    </div>
  );
}

export default App;
