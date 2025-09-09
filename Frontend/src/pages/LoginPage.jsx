import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

const LoginPage = ({ onLogin }) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    if (!username || !password) {
      setError("Username and Password are required.");
      setIsLoading(false);
      return;
    }

    try {
      const success = await onLogin(username, password);
      if (!success) {
        throw new Error("Login failed");
      }
      navigate("/chat");
    } catch (err) {
      console.error("Login error:", err);
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <form onSubmit={handleSubmit} style={styles.form}>
        <h2 style={styles.heading}>Login</h2>
        {error && <div style={styles.error}>{error}</div>}

        <div style={styles.field}>
          <label style={styles.label}>Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={styles.input}
            disabled={isLoading}
          />
        </div>

        <div style={styles.field}>
          <label style={styles.label}>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={styles.input}
            disabled={isLoading}
          />
        </div>

        <button type="submit" style={styles.button} disabled={isLoading}>
          {isLoading ? (
            <div style={styles.spinnerContainer}>
              <div style={styles.spinner}></div>
              <span>Logging in...</span>
            </div>
          ) : (
            "Login"
          )}
        </button>
      </form>
    </div>
  );
};

const styles = {
  container: {
    height: "100vh",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    background: "#f0f2f5",
    fontFamily: "Poppins, sans-serif",
  },
  form: {
    background: "#fff",
    padding: "40px",
    borderRadius: "10px",
    boxShadow: "0 0 15px rgba(0,0,0,0.1)",
    width: "100%",
    maxWidth: "400px",
  },
  heading: {
    marginBottom: "20px",
    textAlign: "center",
    color: "#333",
  },
  field: {
    marginBottom: "20px",
  },
  label: {
    display: "block",
    marginBottom: "6px",
    fontWeight: 500,
    color: "#555",
  },
  input: {
    width: "100%",
    padding: "10px 12px",
    borderRadius: "5px",
    border: "1px solid #ccc",
    fontSize: "16px",
    transition: "border 0.3s",
    "&:focus": {
      borderColor: "#007bff",
      outline: "none",
    },
    "&:disabled": {
      backgroundColor: "#f5f5f5",
    },
  },
  button: {
    width: "100%",
    padding: "12px",
    backgroundColor: "#007bff",
    color: "#fff",
    border: "none",
    borderRadius: "5px",
    fontSize: "16px",
    cursor: "pointer",
    transition: "background-color 0.3s",
    "&:hover": {
      backgroundColor: "#0056b3",
    },
    "&:disabled": {
      backgroundColor: "#b3d7ff",
      cursor: "not-allowed",
    },
  },
  error: {
    color: "#dc3545",
    marginBottom: "15px",
    fontSize: "14px",
    textAlign: "center",
    padding: "10px",
    backgroundColor: "#f8d7da",
    borderRadius: "5px",
    border: "1px solid #f5c6cb",
  },
  spinnerContainer: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
  },
  spinner: {
    width: "16px",
    height: "16px",
    border: "2px solid rgba(255,255,255,0.3)",
    borderTopColor: "white",
    borderRadius: "50%",
    animation: "spin 1s linear infinite",
  },
  "@keyframes spin": {
    to: { transform: "rotate(360deg)" },
  },
};

export default LoginPage;
