import React, { useEffect, useState, useRef } from "react";
import { Routes, Route, Navigate, useNavigate } from "react-router-dom";
import axios from "axios";
import ChatbotPage from "./ChatbotPage";
import Unauthorized from "./Unauthorized";
import LoginPage from "./LoginPage";
import PrivateRoute from "./PrivateRoute";
import {
  saveTokenInfo,
  saveLoginInfo,
  getToken,
  getLogin,
  getUserLoginValueFromCookie,
  clearCookies,
} from "../utils/cookie";
import { BASE_URL } from "../services/configService";

const App = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(null);
  const [userDetails, setUserDetails] = useState(null);
  const [loadingMessage, setLoadingMessage] = useState("Initializing...");
  const navigate = useNavigate();
  const hasRun = useRef(false);

  const clearAuthCookies = () => {
    clearCookies();
    setIsAuthenticated(false);
    setUserDetails(null);
  };

  const handleLogout = () => {
    clearAuthCookies();
    setIsAuthenticated(false);
    setUserDetails(null);
    window.location.replace("/login");
  };

  const RedirectToLogin = () => {
    const navigate = useNavigate();
    useEffect(() => {
      const timer = setTimeout(() => {
        navigate("/login", { replace: true });
      }, 2000); // 2 seconds
      return () => clearTimeout(timer);
    }, [navigate]);

    return null;
  };

  const handleLogin = async (username, password, loginType = "pos") => {
    try {
      setLoadingMessage("Authenticating...");
      const code = "act2"; // Match what you had in LoginPage
      const tokenRes = await axios.get(`${BASE_URL}/api/token?Code=${code}`);
      const { access_token, expires } = tokenRes.data;

      setLoadingMessage("Logging in...");
      const loginRes = await axios.post(
        `${BASE_URL}/api/login`,
        {
          username,
          password,
          LoginType: loginType,
        },
        {
          headers: {
            Authorization: `Bearer ${access_token}`,
            "Content-Type": "application/json",
          },
        }
      );

      if (loginRes.status === 200) {
        debugger;
        setUserDetails(loginRes.data);
        setIsAuthenticated(true);
        saveTokenInfo(access_token, expires);
        saveLoginInfo(loginRes.data.Name);
        return true;
      } else {
        throw new Error("Login failed");
      }
    } catch (err) {
      console.error("Login error:", err);
      
      // Get the actual error message from the backend
      let errorMessage = "Login failed";
      if (err.response && err.response.data && err.response.data.error) {
        errorMessage = err.response.data.error;
      }
      
      clearAuthCookies();
      throw new Error(errorMessage); // This will show the actual error
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const urlLogin = params.get("login");

    // Always run if code and login are in URL
    if (hasRun.current && !(code && urlLogin)) return;
    hasRun.current = true;

    const checkAuth = async () => {
      if (code && urlLogin) {
        try {
          setLoadingMessage("Authenticating...");
          const tokenRes = await axios.get(
            `${BASE_URL}/api/token?Code=${code}`
          );
          const { access_token, expires } = tokenRes.data;

          setLoadingMessage("Logging in...");
          const encodedLogin = encodeURIComponent(urlLogin);
          const loginRes = await axios.post(
            `${BASE_URL}/api/login`,
            {
              EncryptedCred: encodedLogin,
              LoginType: "wms",
            },
            {
              headers: {
                Authorization: `Bearer ${access_token}`,
                "Content-Type": "application/x-www-form-urlencoded",
              },
            }
          );

          if (loginRes.status === 200) {
            setUserDetails(loginRes.data);
            setIsAuthenticated(true);
            saveTokenInfo(access_token, expires);
            saveLoginInfo(loginRes.data.Name);
            navigate("/chat", { replace: true });
          } else {
            throw new Error("WMS login failed");
          }
        } catch (err) {
          console.error("WMS login error:", err);
          clearAuthCookies();
          navigate("/unauthorized", { replace: true });
        }
        return;
      }

      const cookies_token = getToken();
      const cookies_login = getLogin();
      const cookie_user_Login = getUserLoginValueFromCookie();

      if (cookies_login && cookies_token) {
        setUserDetails({
          Name: cookie_user_Login,
        });
        setIsAuthenticated(true);
        navigate("/chat", { replace: true });
        return;
      } else {
        setIsAuthenticated(false);
      }
    };

    checkAuth();

    const handlePopState = () => {
      if (!isAuthenticated && window.location.pathname !== "/unauthorized") {
        navigate("/unauthorized", { replace: true });
      }
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [isAuthenticated, navigate]);

  if (isAuthenticated === null) {
    return (
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          height: "100vh",
          width: "100vw",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
          backgroundColor: "#f4f4f4",
          zIndex: 9999,
          fontFamily: "Poppins, sans-serif",
        }}
      >
        <div
          style={{
            width: "48px",
            height: "48px",
            border: "5px solid #ccc",
            borderTopColor: "#007bff",
            borderRadius: "50%",
            animation: "spin 1s linear infinite",
            marginBottom: "20px",
          }}
        />
        <p style={{ fontSize: "20px", fontWeight: "500", color: "#333" }}>
          {loadingMessage}
        </p>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return (
    <Routes>
      <Route
        path="/"
        element={
          isAuthenticated ? (
            <Navigate to="/chat" replace />
          ) : (
            <LoginPage onLogin={handleLogin} setUserDetails={setUserDetails} />
          )
        }
      />
      <Route
        path="/login"
        element={
          <LoginPage onLogin={handleLogin} setUserDetails={setUserDetails} />
        }
      />
      <Route
        path="/chat"
        element={
          <PrivateRoute isAuthenticated={isAuthenticated}>
            <ChatbotPage user={userDetails} onLogout={handleLogout} />
          </PrivateRoute>
        }
      />
      <Route
        path="/logout"
        element={
          <div
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              width: "100vw",
              height: "100vh",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              backgroundColor: "white",
              fontFamily: "Poppins, sans-serif",
            }}
          >
            <div style={{ textAlign: "center" }}>
              <h2>Logged Out Successfully</h2>
              <p>Redirecting to login...</p>
            </div>
            <RedirectToLogin />
          </div>
        }
      />

      <Route path="/unauthorized" element={<Unauthorized />} />
    </Routes>
  );
};

export default App;