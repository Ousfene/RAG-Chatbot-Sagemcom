// src/AuthContext.jsx
import React, { createContext, useContext, useEffect, useState } from "react";

const DEFAULT_CRED = { username: "sagecomUser", password: "sagecomUser" };

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);

  // On mount, only restore session if it was saved with remember === true
  useEffect(() => {
    try {
      const saved = localStorage.getItem("sagemcom_session");
      if (saved) {
        const parsed = JSON.parse(saved);
        // parsed should be like: { username: '...', remember: true }
        if (parsed?.username && parsed?.remember) {
          setUser({ username: parsed.username });
          setIsAuthenticated(true);
        } else {
          // do not restore if remember is false (or missing)
          localStorage.removeItem("sagemcom_session");
        }
      }
    } catch (e) {
      // ignore parse errors and don't auto-login
      localStorage.removeItem("sagemcom_session");
    }
  }, []);

  // login returns { ok, error } for the caller to react
  const login = ({ username, password }, remember = false) => {
    if (username === DEFAULT_CRED.username && password === DEFAULT_CRED.password) {
      setUser({ username });
      setIsAuthenticated(true);
      if (remember) {
        localStorage.setItem("sagemcom_session", JSON.stringify({ username, remember: true }));
      } else {
        // ensure nothing persisted if user didn't choose remember
        localStorage.removeItem("sagemcom_session");
      }
      return { ok: true };
    }
    return { ok: false, error: "Identifiants incorrects" };
  };

  const logout = () => {
    setUser(null);
    setIsAuthenticated(false);
    localStorage.removeItem("sagemcom_session");
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
