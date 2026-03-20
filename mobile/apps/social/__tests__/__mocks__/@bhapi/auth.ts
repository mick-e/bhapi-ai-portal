export const tokenManager = {
  getToken: jest.fn().mockResolvedValue(null),
  setToken: jest.fn().mockResolvedValue(undefined),
  clearToken: jest.fn().mockResolvedValue(undefined),
  isAuthenticated: jest.fn().mockResolvedValue(false),
  _setStore: jest.fn(),
  _resetStore: jest.fn(),
};
