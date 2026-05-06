import React from 'react'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-caption text-content-secondary mb-1.5">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={`
            w-full h-10 px-3.5 bg-surface-page border border-border rounded-md
            text-body text-content-primary placeholder-content-tertiary
            transition-all duration-200
            focus:border-brand focus:ring-2 focus:ring-brand/15 focus:outline-none
            disabled:opacity-50 disabled:cursor-not-allowed
            ${error ? 'border-error focus:border-error focus:ring-error/20' : ''}
            ${className}
          `}
          {...props}
        />
        {error && (
          <p className="mt-1 text-label text-error">{error}</p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'
