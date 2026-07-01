// src/Login.jsx
import React, { useState, useRef, useEffect } from "react";
import { useAuth } from "./AuthContext";
import logo from "./assets/logo-sagemcom-new-charte-header.png";
import "./login.css";

const DEFAULT_USER = "sagecomUser";
const ANIM_MS = 420; // must match CSS animation duration

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState(DEFAULT_USER);
  const [password, setPassword] = useState(DEFAULT_USER);
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [isLeaving, setIsLeaving] = useState(false);
  const userRef = useRef(null);
  const animTimeout = useRef(null);

  useEffect(() => {
    userRef.current?.focus();
    return () => clearTimeout(animTimeout.current);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    // small UX delay (shows spinner if desired)
    setTimeout(() => {
      // simple credentials check (matches your existing flow)
      if (username === DEFAULT_USER && password === DEFAULT_USER) {
        // play leaving animation
        setIsLeaving(true);

        // after animation, perform login() so App will show chat
        animTimeout.current = setTimeout(() => {
          login({ username, password }, remember);
        }, ANIM_MS + 30);
      } else {
        setLoading(false);
        setError("Identifiants incorrects");
      }
    }, 200);
  };

  return (
    <div className="login-page" role="main" aria-labelledby="loginTitle">
      <div
        className={`login-card ${isLeaving ? "leave" : "enter"}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="loginTitle"
      >
        <div className="login-logo">
          <img src={logo} alt="Sagemcom Logo" />
          <div className="login-brand">
            <h2 id="loginTitle" className="gold-title">Connexion</h2>
            <div className="login-sub">Sagemcom Qualité</div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="login-form" autoComplete="on">
          <label>
            Nom d'utilisateur
            <input
              ref={userRef}
              name="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              aria-label="Nom d'utilisateur"
              required
            />
          </label>

          <label>
            Mot de passe
            <input
              name="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              aria-label="Mot de passe"
              required
            />
          </label>

          <label className="remember-row">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              aria-label="Se souvenir de moi"
            />
            Se souvenir
          </label>

          {error && <div className="login-error" role="alert">{error}</div>}

          <div className="login-actions">
            <div className="login-empty" />
            <button type="submit" disabled={loading} aria-disabled={loading}>
              {loading ? "Connexion…" : "Se connecter"}
            </button>
          </div>
        </form>

        <div className="login-note">
          <small>Utiliser : <strong>{DEFAULT_USER}</strong> / <strong>{DEFAULT_USER}</strong></small>
        </div>
      </div>
    </div>
  );
}
