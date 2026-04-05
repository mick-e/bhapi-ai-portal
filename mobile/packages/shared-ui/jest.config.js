module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  testPathIgnorePatterns: ['__mocks__'],
  moduleNameMapper: {
    '^react-native$': '<rootDir>/__tests__/__mocks__/react-native',
    '^react$': '<rootDir>/__tests__/__mocks__/react',
    '^@react-native-async-storage/async-storage$': '<rootDir>/__tests__/__mocks__/async-storage',
  },
};
