module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  testPathIgnorePatterns: ['__mocks__'],
  moduleNameMapper: {
    '^react-native$': '<rootDir>/__tests__/__mocks__/react-native',
    '^react$': '<rootDir>/__tests__/__mocks__/react',
    '^@bhapi/config$': '<rootDir>/../../packages/shared-config/src',
    '^@bhapi/auth$': '<rootDir>/__tests__/__mocks__/@bhapi/auth',
    '^@bhapi/ui$': '<rootDir>/__tests__/__mocks__/@bhapi/ui',
    '^@bhapi/types$': '<rootDir>/../../packages/shared-types/src',
    '^@bhapi/api$': '<rootDir>/__tests__/__mocks__/@bhapi/api',
  },
};
