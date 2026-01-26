# 006 - React Project Setup

## Metadata

```yaml
prompt_id: "006"
phase: 1
agent: "@frontend"
model: "sonnet 4.5"
priority: P0
estimated_effort: "2 days"
dependencies: ["001"]
```

## Objective

Initialize the React frontend project with Vite, TypeScript, Tailwind CSS, and Shadcn/UI component library.

## Task Description

Create a production-ready React frontend with:

1. **Vite** - Fast development server and build tool
2. **TypeScript** - Type safety throughout
3. **Tailwind CSS** - Utility-first CSS framework
4. **Shadcn/UI** - Accessible component library
5. **Project Structure** - Feature-based organization

## Requirements

### Initial Setup

```bash
# Create Vite project with TypeScript
npm create vite@latest frontend -- --template react-ts
cd frontend

# Install Tailwind CSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Install Shadcn/UI dependencies
npm install class-variance-authority clsx tailwind-merge
npm install lucide-react @radix-ui/react-icons

# State management and data fetching
npm install zustand @tanstack/react-query @tanstack/react-query-devtools

# Routing
npm install react-router-dom

# Forms
npm install react-hook-form @hookform/resolvers zod
```

### TypeScript Configuration

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### Tailwind Configuration

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class'],
  content: [
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        // ... other colors
      },
    },
  },
  plugins: [],
}
export default config
```

## Expected Output

```
frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── ui/               # Shadcn/UI components
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── card.tsx
│   │   │   └── ...
│   │   └── common/           # Shared components
│   ├── features/             # Feature modules
│   ├── hooks/                # Custom hooks
│   ├── lib/                  # Utilities
│   │   ├── utils.ts
│   │   └── api.ts
│   ├── store/                # Zustand stores
│   ├── types/                # TypeScript types
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── index.html
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
└── vite.config.ts
```

## Acceptance Criteria

- [ ] `npm run dev` starts development server
- [ ] TypeScript compilation succeeds
- [ ] Tailwind classes work correctly
- [ ] Path aliases resolve (@/* imports)
- [ ] Shadcn/UI Button component renders
- [ ] Hot Module Replacement (HMR) works
- [ ] Production build succeeds (`npm run build`)

## Reference Documents

- [Frontend Agent](../agents/frontend-agent.agent.md)
- [React Components Skill](../skills/react-components/SKILL.md)
