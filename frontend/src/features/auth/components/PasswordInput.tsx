import { useState, forwardRef, InputHTMLAttributes } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export interface PasswordInputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  showStrength?: boolean
}

export const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ className, showStrength = false, ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false)
    const [strength, setStrength] = useState(0)

    const calculateStrength = (password: string): number => {
      let score = 0
      if (password.length >= 8) score++
      if (password.length >= 12) score++
      if (/[a-z]/.test(password)) score++
      if (/[A-Z]/.test(password)) score++
      if (/[0-9]/.test(password)) score++
      if (/[^a-zA-Z0-9]/.test(password)) score++
      return Math.min(score, 4)
    }

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      if (showStrength) {
        setStrength(calculateStrength(e.target.value))
      }
      props.onChange?.(e)
    }

    const getStrengthColor = (level: number): string => {
      const colors = ['bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-green-500']
      return colors[level - 1] || 'bg-gray-200'
    }

    const getStrengthLabel = (level: number): string => {
      const labels = ['Weak', 'Fair', 'Good', 'Strong']
      return labels[level - 1] || ''
    }

    return (
      <div className="space-y-2">
        <div className="relative">
          <Input
            ref={ref}
            type={showPassword ? 'text' : 'password'}
            className={cn('pr-10', className)}
            {...props}
            onChange={handleChange}
          />
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
            onClick={() => setShowPassword(!showPassword)}
            tabIndex={-1}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? (
              <EyeOff className="h-4 w-4 text-muted-foreground" />
            ) : (
              <Eye className="h-4 w-4 text-muted-foreground" />
            )}
          </Button>
        </div>
        
        {showStrength && props.value && (
          <div className="space-y-1">
            <div className="flex gap-1">
              {[1, 2, 3, 4].map((level) => (
                <div
                  key={level}
                  className={cn(
                    'h-1 flex-1 rounded-full transition-colors',
                    level <= strength ? getStrengthColor(strength) : 'bg-gray-200'
                  )}
                />
              ))}
            </div>
            {strength > 0 && (
              <p className="text-xs text-muted-foreground">
                Password strength: {getStrengthLabel(strength)}
              </p>
            )}
          </div>
        )}
      </div>
    )
  }
)

PasswordInput.displayName = 'PasswordInput'
