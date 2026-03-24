// Mock @tanstack/react-query for testing without a QueryClient
export function useQuery(_options: any) {
  return {
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    refetch: jest.fn(),
  };
}

export function useMutation(_options: any) {
  return {
    mutate: jest.fn(),
    mutateAsync: jest.fn(),
    isPending: false,
    isError: false,
    error: null,
    reset: jest.fn(),
  };
}

export function useQueryClient() {
  return {
    invalidateQueries: jest.fn(),
    setQueryData: jest.fn(),
    getQueryData: jest.fn(),
  };
}

export function QueryClient() {}
export const QueryClientProvider = 'QueryClientProvider';
