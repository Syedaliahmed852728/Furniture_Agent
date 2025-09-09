import React from "react";

const Unauthorized = () => (
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
      flexDirection: "column",
      backgroundColor: "white",
      fontFamily: "Poppins, sans-serif",
    }}
  >
    <div style={{ textAlign: "center" }}>
      <h2>Access Denied</h2>
      <p>Please Login to continue.</p>
    </div>
  </div>
);

export default Unauthorized;
