/** Маршрут переадресации после успешного входа */
export const POST_LOGIN_REDIRECT = "/dashboard";

export const ROUTES = {
  home: "/",
  login: "/login",
  register: "/register",
  dashboard: POST_LOGIN_REDIRECT,
} as const;
