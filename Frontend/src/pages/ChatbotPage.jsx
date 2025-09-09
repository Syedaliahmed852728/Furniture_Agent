import React, { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import "../assets/ChatbotPage.css";
import { clearCookies, getTokenFromCookie } from "../utils/cookie.js";
import axios from "axios";
import { BASE_URL } from "../services/configService";

import html2canvas from "html2canvas";
import jsPDF from "jspdf";
import * as XLSX from "xlsx";

const ChatbotPage = ({ user }) => {
  const [isSidebarOpen, setSidebarOpen] = useState(true);
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const [savedChats, setSavedChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  const messagesEndRef = useRef(null);
  const cookieToken = getTokenFromCookie();

  const fetchSavedChats = async () => {
    try {
      if (!user?.ContactID) return;
      const response = await axios.get(
        `${BASE_URL}/api/chat/history/${user.ContactID}`,
        {
          headers: { Authorization: `Bearer ${cookieToken}` },
        }
      );
      setSavedChats(response.data);
      console.log("Saved chats fetched successfully:", response.data);
    } catch (error) {
      console.error("Failed to fetch saved chats:", error);
    }
  };

  useEffect(() => {
    fetchSavedChats();
  }, [user]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  const handleLogout = () => {
    clearCookies();
    navigate("/Logout");
  };

  const handleNewChat = () => {
    setActiveChatId(null);
    setChatHistory([]);
  };

  const handleSelectChat = (chat) => {
    setActiveChatId(chat.ChatId);
    const formattedHistory = chat.Messages.map((msg) => ({
      id: msg.MessageId,
      question: msg.Content,
      response: null,
      error: null,
    }));
    setChatHistory(formattedHistory);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const currentQuestion = question.trim();
    if (!currentQuestion || isLoading) return;

    setIsLoading(true);

    const newTurn = {
      id: Date.now(),
      question: currentQuestion,
      response: null,
      error: null,
    };
    setChatHistory((prev) => [...prev, newTurn]);
    setQuestion("");

    try {
      // First make the query API call
      const res = await axios.post(
        `${BASE_URL}/api/query`,
        { question: currentQuestion },
        { headers: { Authorization: `Bearer ${cookieToken}` } }
      );

      // Update chat history with the response
      setChatHistory((prev) =>
        prev.map((turn) =>
          turn.id === newTurn.id ? { ...turn, response: res.data } : turn
        )
      );

      // Now handle saving with the sql_columns from the response
      if (!user?.ContactID) {
        throw new Error(
          "User ID is missing from user session. Cannot save chat."
        );
      }

      let currentChatId = activeChatId;
      let sql_Attributes = res.data.sql_query_columns; // Get sql_columns from query response

      console.log("SQL Attributes to save:", sql_Attributes);

      if (!currentChatId) {
        const saveRes = await axios.post(
          `${BASE_URL}/api/chat/save`,
          {
            chatId: null,
            userId: user.ContactID,
            chatContent:
              currentQuestion.substring(0, 40) +
              (currentQuestion.length > 40 ? "..." : ""),
            messageContent: currentQuestion,
            sqlAttributes: sql_Attributes, // Add sql_columns to save payload
          },
          { headers: { Authorization: `Bearer ${cookieToken}` } }
        );
        const newChatId = saveRes.data.ChatId;
        setActiveChatId(newChatId);
        fetchSavedChats();
      } else {
        await axios.post(
          `${BASE_URL}/api/chat/save`,
          {
            chatId: currentChatId,
            userId: user.ContactID,
            messageContent: currentQuestion,
            sqlAttributes: sql_Attributes, // Add sql_columns to save payload
          },
          { headers: { Authorization: `Bearer ${cookieToken}` } }
        );
        fetchSavedChats();
      }
    } catch (err) {
      console.error("Error:", err);
      setChatHistory((prev) =>
        prev.map((turn) =>
          turn.id === newTurn.id
            ? { ...turn, error: err.message || "An error occurred" }
            : turn
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  const formatCellContent = (value) => {
    if (value === null || value === undefined) return "N/A";
    if (typeof value === "number")
      return value.toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
    return String(value);
  };

  const downloadChartPDF = async (turnId) => {
    const chart = document.getElementById(`chart-container-${turnId}`);
    if (!chart) return;
    const canvas = await html2canvas(chart);
    const imgData = canvas.toDataURL("image/png");
    const pdf = new jsPDF({ orientation: "landscape" });
    pdf.addImage(imgData, "PNG", 10, 10, 280, 150);
    pdf.save(`chart-${turnId}.pdf`);
  };

  const downloadTableExcel = (turnId) => {
    const table = document.getElementById(`data-table-${turnId}`);
    if (!table) return;
    const wb = XLSX.utils.table_to_book(table, { sheet: "Data" });
    XLSX.writeFile(wb, `table-${turnId}.xlsx`);
  };

  const containerClassName = isSidebarOpen
    ? "chat-container"
    : "chat-container sidebar-closed";

  return (
    <div className={containerClassName}>
      <aside className="sidebar">
        <div className="sidebar-content-wrapper">
          <header className="sidebar-profile">
            <p>
              Logged in as: <strong>{user?.Name}</strong>
            </p>
            <button
              onClick={handleLogout}
              className="logout-btn"
              title="Logout"
            >
              Logout
            </button>
          </header>

          <div className="sidebar-actions">
            <button onClick={handleNewChat} className="new-chat-btn">
              New Chat
            </button>
          </div>

          <div className="sidebar-footer-info">
            <div className="info-panel">
              <div className="message-content">
                <h2>How SQL Agent Works</h2>
                <ol>
                  <li>
                    <strong>Training</strong>: SQL Agent learns your database
                    schema automatically
                  </li>
                  <li>
                    <strong>Processing</strong>: Your natural language question
                    is analyzed
                  </li>
                  <li>
                    <strong>SQL Generation</strong>: AI generates appropriate
                    SQL queries
                  </li>
                  <li>
                    <strong>Execution</strong>: Query runs on your SQL Server
                    database
                  </li>
                  <li>
                    <strong>Results</strong>: Data is returned with explanations
                    and visualizations
                  </li>
                </ol>
                <br />
                <h2>Sample Questions</h2>
                <ul>
                  <li>What is the total sales for June 2025?</li>
                  <li>
                    Show me average ticket sale by region and its total gross
                    earning in May
                  </li>
                  <li>
                    What is the sales count and gross earning by region and
                    status show its trend
                  </li>
                  <li>What is the gross margin of june?</li>
                  <li>Show me sales trends over time</li>
                  <li>What are the top 5 companies by sales?</li>
                </ul>
                <br />
                <h2>Powered by:</h2>
                <p className="powered-by">iVantage360 GenAI</p>
              </div>
            </div>
          </div>
        </div>
        <div className="history-dropdown">
          <div
            className="history-header"
            onClick={() => setIsHistoryOpen(!isHistoryOpen)}
          >
            <span className="menu-item">
              <span role="img" aria-label="history"></span> History
            </span>
            <span className="arrow">{isHistoryOpen ? "▾" : "▸"}</span>
          </div>
          {isHistoryOpen && (
            <div className="conversation-list">
              {savedChats.map((chat) => (
                <div
                  key={chat.ChatId}
                  className={`conversation-item ${
                    activeChatId === chat.ChatId ? "active" : ""
                  }`}
                  onClick={() => handleSelectChat(chat)}
                >
                  {chat.Chat_Content?.substring(0, 30) ||
                    chat.Messages[0]?.Content?.substring(0, 30) ||
                    "Untitled Chat"}
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>

      <main className="chat-main">
        <header className="chat-main-header">
          <button
            className="sidebar-toggle-btn"
            onClick={() => setSidebarOpen(!isSidebarOpen)}
            title="Toggle Sidebar"
          >
            <svg
              stroke="currentColor"
              fill="currentColor"
              strokeWidth="0"
              viewBox="0 0 24 24"
              height="1em"
              width="1em"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"></path>
            </svg>
          </button>
        </header>

        <div className="chat-content-area">
          <div className="chat-messages">
            <div className="welcome-message">
              <h1>SQL Database Chatbot</h1>
            </div>

            {chatHistory.length > 0 &&
              chatHistory.map((turn) => (
                <React.Fragment key={turn.id}>
                  <div className="question-wrapper">
                    <p className="question-box">{turn.question}</p>
                  </div>
                  {turn.error && <p className="error-message">{turn.error}</p>}
                  {turn.response && (
                    <div className="chat-response">
                      {turn.response.columns?.length > 0 &&
                        turn.response.table?.length > 0 && (
                          <div className="table-section">
                            <header className="section-header">
                              <h2 className="section-heading">Table Results</h2>
                              <button
                                onClick={() => downloadTableExcel(turn.id)}
                                className="export-btn"
                              >
                                Export as Excel
                              </button>
                            </header>
                            <div className="table-container">
                              <table
                                className="styled-table"
                                id={`data-table-${turn.id}`}
                              >
                                <thead>
                                  <tr>
                                    {turn.response.columns.map((col) => (
                                      <th key={col}>{col}</th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {turn.response.table.map((row, idx) => (
                                    <tr key={idx}>
                                      {turn.response.columns.map((col) => (
                                        <td key={col}>
                                          {formatCellContent(row[col])}
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        )}
                      {turn.response.chart_url && (
                        <div className="chart-section">
                          <header className="section-header">
                            <h2 className="section-heading">
                              {turn.response.chart_title ||
                                "Chart Visualization"}
                            </h2>
                            <button
                              onClick={() => downloadChartPDF(turn.id)}
                              className="export-btn"
                            >
                              Export as PDF
                            </button>
                          </header>
                          <div
                            className="chart-container"
                            id={`chart-container-${turn.id}`}
                          >
                            <img
                              src={turn.response.chart_url}
                              alt={turn.response.chart_title || "Chart"}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </React.Fragment>
              ))}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="chat-input-area">
          <form className="chat-input-form" onSubmit={handleSubmit}>
            <input
              type="text"
              className="chat-input"
              placeholder="Ask a question about your data..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
            <button
              type="submit"
              className="send-btn"
              title="Send"
              disabled={isLoading}
            >
              {isLoading ? (
                <div className="loader"></div>
              ) : (
                <svg
                  stroke="currentColor"
                  fill="white"
                  strokeWidth="0"
                  viewBox="0 0 512 512"
                  height="1em"
                  width="1em"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path d="M476 3.2L12.5 270.6c-18.1 10.4-15.8 35.6 2.2 43.2L121 358.4l287.3-253.2c5.5-4.9 13.3 2.6 8.6 8.3L176 407v80.5c0 23.6 28.5 32.9 42.5 15.8L282 426l124.6 52.2c14.2 6 30.4-2.9 33-18.2l72-432C515 7.8 493.3-6.8 476 3.2z"></path>
                </svg>
              )}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
};

export default ChatbotPage;
