import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test/test-utils'
import AnalysisForm from '../components/forms/AnalysisForm'

// Mock the analyze hook
vi.mock('../hooks/useAnalyzeResume', () => ({
  default: () => ({
    analyzeResume: vi.fn().mockResolvedValue({
      match_percentage: 75,
      matched_keywords: ['Python', 'React'],
      missing_keywords: ['Docker'],
      suggestions: ['Add Docker experience'],
      strengths: ['Strong programming skills'],
      improved_bullets: ['Enhanced bullet point']
    }),
    loading: false,
    error: null
  })
}))

describe('AnalysisForm', () => {
  it('renders form elements correctly', () => {
    render(<AnalysisForm />)
    
    // Check for main form elements
    expect(screen.getByText(/resume input/i)).toBeInTheDocument()
    expect(screen.getByText(/job description/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /analyze/i })).toBeInTheDocument()
  })

  it('shows sample data button', () => {
    render(<AnalysisForm />)
    
    expect(screen.getByText(/use sample data/i)).toBeInTheDocument()
  })

  it('allows text input in resume field', async () => {
    const user = userEvent.setup()
    render(<AnalysisForm />)
    
    const resumeInput = screen.getByPlaceholderText(/paste your resume/i)
    await user.type(resumeInput, 'Test resume content')
    
    expect(resumeInput).toHaveValue('Test resume content')
  })

  it('allows text input in job description field', async () => {
    const user = userEvent.setup()
    render(<AnalysisForm />)
    
    const jobInput = screen.getByPlaceholderText(/paste the job description/i)
    await user.type(jobInput, 'Test job description')
    
    expect(jobInput).toHaveValue('Test job description')
  })

  it('enables analyze button when both fields have content', async () => {
    const user = userEvent.setup()
    render(<AnalysisForm />)
    
    const resumeInput = screen.getByPlaceholderText(/paste your resume/i)
    const jobInput = screen.getByPlaceholderText(/paste the job description/i)
    const analyzeButton = screen.getByRole('button', { name: /analyze/i })
    
    // Initially disabled
    expect(analyzeButton).toBeDisabled()
    
    // Add content to both fields
    await user.type(resumeInput, 'Resume content')
    await user.type(jobInput, 'Job description')
    
    // Should be enabled now
    await waitFor(() => {
      expect(analyzeButton).not.toBeDisabled()
    })
  })

  it('fills sample data when sample button clicked', async () => {
    const user = userEvent.setup()
    render(<AnalysisForm />)
    
    const sampleButton = screen.getByText(/use sample data/i)
    await user.click(sampleButton)
    
    const resumeInput = screen.getByPlaceholderText(/paste your resume/i)
    const jobInput = screen.getByPlaceholderText(/paste the job description/i)
    
    // Should have sample content
    await waitFor(() => {
      expect(resumeInput.value.length).toBeGreaterThan(0)
      expect(jobInput.value.length).toBeGreaterThan(0)
    })
  })
})