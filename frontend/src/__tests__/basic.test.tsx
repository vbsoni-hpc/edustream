import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

// A simple dummy component to verify React testing works
function TestComponent() {
  return <div><h1>Hello EduStream</h1></div>;
}

describe('Basic Test', () => {
  it('renders correctly', () => {
    render(<TestComponent />);
    expect(screen.getByText('Hello EduStream')).toBeInTheDocument();
  });
});
