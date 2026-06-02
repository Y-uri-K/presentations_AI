export const POST_LOGIN_REDIRECT = "/dashboard";

export const ROUTES = {
  home: "/",
  login: "/login",
  register: "/register",
  forgotPassword: "/forgot-password",
  dashboard: POST_LOGIN_REDIRECT,
  profile: "/profile",
} as const;
