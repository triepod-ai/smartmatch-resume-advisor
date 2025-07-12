import axios from 'axios';
import { AnalysisRequest, AnalysisResponse } from '../types';

const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'https://your-backend-url.com' 
  : 'http://127.0.0.1:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout for analysis
});

export const analyzeResume = async (data: AnalysisRequest): Promise<AnalysisResponse> => {
  try {
    const response = await apiClient.post<AnalysisResponse>('/analyze', data);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const message = error.response?.data?.detail || error.message;
      throw new Error(`Analysis failed: ${message}`);
    }
    throw new Error('An unexpected error occurred during analysis');
  }
};

export const checkHealth = async (): Promise<{ status: string }> => {
  try {
    const response = await apiClient.get('/health');
    return response.data;
  } catch {
    throw new Error('Backend health check failed');
  }
};