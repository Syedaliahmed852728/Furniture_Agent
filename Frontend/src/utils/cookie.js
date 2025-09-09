import Cookies from "js-cookie";
const COOKIE_Token_NAME = "sales_bot_token";
const COOKIE_Login_NAME = "sales_bot_login";


export const getToken = () => {
  return Cookies.get(COOKIE_Token_NAME);
};

export const getLogin = () => {
  return Cookies.get(COOKIE_Login_NAME);
};

export function saveLoginInfo(userLogin, ContactID) {
  const cookieLoginData = {
    user_Login: userLogin,
    ContactID: ContactID
  };
  Cookies.set(COOKIE_Login_NAME, JSON.stringify(cookieLoginData), { expires: 1 });
}

export function saveTokenInfo(userToken, expires) {
  const cookieData = {
    token_expires_at: expires,
    user_token: userToken,
  };
  Cookies.set(COOKIE_Token_NAME, JSON.stringify(cookieData), { expires: 1 });
}

export function getTokenInfo() {
  const cookie = Cookies.get(COOKIE_Token_NAME);
  if (!cookie) return null;

  try {
    const data = JSON.parse(cookie);
    const expiry = new Date(data.token_expires_at);
    if (expiry > new Date()) {
      return data.user_details;
    }
  } catch {
    return null;
  }

  return null;
}

export function getLoginInfo() {
  const cookie = Cookies.get(COOKIE_Login_NAME);
  if (!cookie) return null;

  try {
    const data = JSON.parse(cookie);
    const expiry = new Date(data.token_expires_at);
    if (expiry > new Date()) {
      return data.user_details;
    }
  } catch {
    return null;
  }

  return null;
}

export function getUserLoginValueFromCookie() {
  if (getLogin()) {
    try {
      var login = getLogin();
      const parsed = JSON.parse(login);
      return parsed.user_Login;

    } catch (error) {
      console.error('Error decoding user login:', error);
      return null;
    }
  }

}

export function getContactValueFromCookie() {
  if (getLogin()) {
    try {
      var login = getLogin();
      const parsed = JSON.parse(login);
      return parseInt(parsed.ContactID, 10);

    } catch (error) {
      console.error('Error decoding user login:', error);
      return null;
    }
  }

}

export function getTokenFromCookie() {
  if (getToken()) {
    try {
      const tokenData = getToken();

      const parsed = JSON.parse(tokenData);

      return parsed.user_token;

    } catch (error) {
      console.error('Error decoding user token:', error);
      return null;
    }
  }

}

export function getCookie(name) {
  if (typeof document === 'undefined') return null;

  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}


export function clearCookies() {
  Cookies.remove(COOKIE_Token_NAME);
  Cookies.remove(COOKIE_Login_NAME);

  document.cookie.split(";").forEach((cookie) => {
    const name = cookie.split("=")[0].trim();
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/`;
  });

  localStorage.clear();
  sessionStorage.clear();
}