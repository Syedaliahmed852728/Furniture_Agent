import React, { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { getTokenFromCookie, getUserLoginValueFromCookie } from "../utils/cookie";

const PrivateRoute = ({ children }) => {
  const [isAllowed, setIsAllowed] = useState(null);

  useEffect(() => {
    const token = getTokenFromCookie();
    const login = getUserLoginValueFromCookie();

    if (!token || !login) {
      setIsAllowed(false);
    } else {
      setIsAllowed(true);
    }
  }, []);

  if (isAllowed === null) return null;

  return isAllowed ? children : <Navigate to="/login" replace />;
};

export default PrivateRoute;