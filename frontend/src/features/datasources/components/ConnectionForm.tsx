import { UseFormReturn } from 'react-hook-form'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Textarea } from '@/components/ui/textarea'
import { Eye, EyeOff, Info } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

interface ConnectionFormProps {
  form: UseFormReturn<any>
  onSubmit: (data: any) => void
}

export function ConnectionForm({ form, onSubmit }: ConnectionFormProps) {
  const [showPassword, setShowPassword] = useState(false)
  
  const {
    register,
    formState: { errors },
    watch,
    setValue,
  } = form

  const sslEnabled = watch('ssl_enabled')
  const dbType = watch('db_type')
  const thickMode = watch('thick_mode')

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
      <div className="grid gap-4">
        {/* Name */}
        <div className="space-y-2">
          <Label htmlFor="name">
            Connection Name <span className="text-destructive">*</span>
          </Label>
          <Input
            id="name"
            placeholder="My Production Database"
            {...register('name')}
            className={errors.name ? 'border-destructive' : ''}
          />
          {errors.name && (
            <p className="text-sm text-destructive">{errors.name.message as string}</p>
          )}
        </div>

        {/* Host and Port */}
        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2 space-y-2">
            <Label htmlFor="host">
              Host <span className="text-destructive">*</span>
            </Label>
            <Input
              id="host"
              placeholder="localhost or db.example.com"
              {...register('host')}
              className={errors.host ? 'border-destructive' : ''}
            />
            {errors.host && (
              <p className="text-sm text-destructive">{errors.host.message as string}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="port">
              Port <span className="text-destructive">*</span>
            </Label>
            <Input
              id="port"
              type="number"
              {...register('port', { valueAsNumber: true })}
              className={errors.port ? 'border-destructive' : ''}
            />
            {errors.port && (
              <p className="text-sm text-destructive">{errors.port.message as string}</p>
            )}
          </div>
        </div>

        {/* Database */}
        <div className="space-y-2">
          <Label htmlFor="database">
            Database <span className="text-destructive">*</span>
          </Label>
          <Input
            id="database"
            placeholder="analytics"
            {...register('database')}
            className={errors.database ? 'border-destructive' : ''}
          />
          {errors.database && (
            <p className="text-sm text-destructive">{errors.database.message as string}</p>
          )}
        </div>

        {/* Username */}
        <div className="space-y-2">
          <Label htmlFor="username">
            Username <span className="text-destructive">*</span>
          </Label>
          <Input
            id="username"
            placeholder="db_user"
            {...register('username')}
            className={errors.username ? 'border-destructive' : ''}
          />
          {errors.username && (
            <p className="text-sm text-destructive">{errors.username.message as string}</p>
          )}
        </div>

        {/* Password */}
        <div className="space-y-2">
          <Label htmlFor="password">
            Password <span className="text-destructive">*</span>
          </Label>
          <div className="relative">
            <Input
              id="password"
              type={showPassword ? 'text' : 'password'}
              placeholder="Enter password"
              {...register('password')}
              className={errors.password ? 'border-destructive pr-10' : 'pr-10'}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4 text-muted-foreground" />
              ) : (
                <Eye className="h-4 w-4 text-muted-foreground" />
              )}
            </Button>
          </div>
          {errors.password && (
            <p className="text-sm text-destructive">{errors.password.message as string}</p>
          )}
        </div>

        {/* SSL */}
        <div className="flex items-center space-x-2">
          <Checkbox
            id="ssl_enabled"
            checked={sslEnabled}
            onCheckedChange={(checked) => setValue('ssl_enabled', checked)}
          />
          <Label
            htmlFor="ssl_enabled"
            className="text-sm font-normal cursor-pointer"
          >
            Enable SSL/TLS encryption (recommended)
          </Label>
        </div>

        {/* Oracle-specific options */}
        {dbType === 'oracle' && (
          <div className="space-y-4 border-t pt-4">
            <h4 className="text-sm font-medium text-muted-foreground">Oracle Options</h4>
            
            {/* Service Name */}
            <div className="space-y-2">
              <Label htmlFor="service_name">
                Service Name
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="inline-block ml-1 h-4 w-4 text-muted-foreground cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent side="right" className="max-w-xs">
                      <p>The Oracle service name. Leave empty to use SID (database field) instead.</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </Label>
              <Input
                id="service_name"
                placeholder="ORCL.example.com (optional)"
                {...register('service_name')}
              />
              <p className="text-xs text-muted-foreground">
                If provided, service_name is used; otherwise, the Database field is treated as SID.
              </p>
            </div>

            {/* Thick Mode */}
            <div className="flex items-center space-x-2">
              <Checkbox
                id="thick_mode"
                checked={thickMode}
                onCheckedChange={(checked) => setValue('thick_mode', checked === true)}
              />
              <Label
                htmlFor="thick_mode"
                className="text-sm font-normal cursor-pointer"
              >
                Enable Thick Mode
              </Label>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent side="right" className="max-w-xs">
                    <p>
                      <strong>Required for Oracle 11g and earlier.</strong><br />
                      Uses Oracle Instant Client for legacy database support. 
                      Enable this if you get "thin mode not supported" errors.
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <p className="text-xs text-muted-foreground">
              Enable for older Oracle databases (11g or earlier) that don't support thin mode.
            </p>
          </div>
        )}
      </div>
    </form>
  )
}
