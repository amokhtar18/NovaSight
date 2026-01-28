# 051 - UI Redesign & Polish

## Purpose

This prompt file contains reusable prompts for implementing the NovaSight UI redesign, following a modern AI/Technology-inspired design system with glass morphism, micro-interactions, and accessibility-first approach.

**Phase:** 6 - Polish & Launch (Weeks 22-23)  
**Owner Agent:** `@frontend`  
**Design Reference:** [Aivent Theme](https://madebydesignesia.com/themes/aivent/index-static-background.html)  
**Implementation Doc:** [IMPLEMENTATION_020_UI_REDESIGN.md](../../docs/implementation/IMPLEMENTATION_020_UI_REDESIGN.md)

---

## 🎨 Design System Prompts

### Prompt: Initialize Design Token System

```
Set up the NovaSight design token system including:
1. Create CSS custom properties in frontend/src/styles/design-tokens.css
2. Configure dark mode as default with light mode toggle
3. Define color palette (background, accent, neon, text, border, glass)
4. Set typography scale with font families (Inter for UI, JetBrains Mono for code)
5. Define spacing, border-radius, and shadow tokens
6. Configure transition timing functions
7. Extend tailwind.config.ts to use design tokens

Use these core colors:
- Background: #0a0a0f (primary), #12121a (secondary), #1a1a25 (tertiary)
- Accent: #6366f1 (indigo), #8b5cf6 (purple), #a855f7 (violet)
- Neon: #22d3ee (cyan), #ec4899 (pink), #10b981 (green)
- Glass: rgba(255, 255, 255, 0.03) with blur backdrop

Follow frontend-agent specifications and Tailwind best practices.
```

### Prompt: Create Animation System

```
Implement the NovaSight animation system with:
1. Create frontend/src/styles/animations.css with keyframe animations
2. Create frontend/src/lib/motion-variants.ts for Framer Motion presets
3. Define micro-interactions (150ms), base (250ms), slow (350ms), spring (500ms)
4. Implement AI-specific animations (pulse, glow, neural-flow, typing-dots)
5. Add page transition variants (fade-up, scale-in, slide)
6. Create stagger container variants for lists
7. Define hover states (lift, glow, magnetic)

Required keyframes:
- ai-pulse: Glowing box-shadow animation for AI elements
- gradient-flow: Moving gradient background
- float: Subtle floating motion for decorative elements
- neural-pulse: SVG stroke animation for network connections

Follow frontend-agent patterns and Framer Motion best practices.
```

---

## 🖼️ Background & Visual Effects Prompts

### Prompt: Create Grid Background Component

```
Create a React background component at frontend/src/components/backgrounds/GridBackground.tsx:
1. SVG pattern grid with subtle lines (opacity 0.1-0.2)
2. Radial gradient overlay from accent color
3. Animated floating orbs with blur effect
4. Pointer-events: none for non-blocking
5. Fixed/absolute positioning options
6. Configurable grid size and colors
7. Performance-optimized with CSS transforms

Include gradient mesh effect similar to Aivent website.
Follow react-components skill patterns.
```

### Prompt: Create Neural Network Background

```
Create an animated neural network component at frontend/src/components/backgrounds/NeuralNetwork.tsx:
1. Generate random node positions
2. Calculate connection lines between nearby nodes
3. Animate connections with stroke-dashoffset
4. Pulse effect on nodes
5. Configurable node count and connection distance
6. SVG-based for crisp rendering
7. RequestAnimationFrame for smooth animation

Use accent gradient for connections and subtle glow on nodes.
Follow frontend-agent specifications.
```

### Prompt: Create Particle System

```
Create a particle effect component at frontend/src/components/backgrounds/ParticleField.tsx:
1. Canvas-based particle rendering
2. Mouse interaction (particles attract/repel)
3. Configurable particle count and colors
4. Connection lines between nearby particles
5. Fade in/out on viewport edges
6. Performance throttling for mobile
7. Cleanup on unmount

Integrate with AI sections for technology aesthetic.
Follow performance best practices.
```

---

## 🧭 Navigation Prompts

### Prompt: Create Collapsible Sidebar

```
Create a collapsible sidebar at frontend/src/components/layout/Sidebar.tsx:
1. Framer Motion animate width (72px collapsed, 280px expanded)
2. Logo area with collapse-aware rendering
3. Navigation items with icon and label
4. Active state with animated indicator (layoutId)
5. Hover states with background transition
6. Nested navigation support (expandable groups)
7. User profile section at bottom
8. Collapse toggle button

Visual requirements:
- Glass morphism background with border
- Active item: accent color background with left border indicator
- Hover: subtle background change
- Icons: 20px, proper alignment

Follow react-components skill and accessibility guidelines.
```

### Prompt: Create Header Component

```
Create a sticky header at frontend/src/components/layout/Header.tsx:
1. Glass morphism background with blur
2. Breadcrumb navigation
3. Global search trigger (Cmd+K shortcut display)
4. Notifications dropdown
5. Theme toggle (dark/light)
6. User avatar menu
7. Mobile menu trigger (responsive)

Animations:
- Slide down on mount
- Background opacity change on scroll
- Dropdown fade/scale transitions

Follow frontend-agent patterns.
```

### Prompt: Create Command Palette

```
Create a command palette at frontend/src/components/layout/CommandPalette.tsx:
1. Use cmdk library with Radix Dialog
2. Register Cmd+K / Ctrl+K keyboard shortcut
3. Search input with icon
4. Command groups (Quick Actions, Navigation, Recent)
5. Keyboard navigation (arrow keys, enter)
6. Fuzzy search filtering
7. Command icons and descriptions
8. Loading state for async commands

Visual requirements:
- Centered modal with backdrop blur
- Glass card styling
- Highlighted matching text
- Selected item background

Follow accessibility guidelines with proper ARIA.
```

### Prompt: Create Mobile Navigation

```
Create mobile navigation at frontend/src/components/layout/MobileNav.tsx:
1. Fixed bottom bar (hidden on md+ breakpoints)
2. 4-5 primary navigation items
3. Active state indicator
4. Sheet/drawer for full menu
5. Swipe gestures for drawer
6. Safe area insets for notched devices
7. Haptic feedback on tap (if supported)

Follow mobile-first design patterns.
```

---

## 🃏 Card & Component Prompts

### Prompt: Create Glass Card Component

```
Create a glass morphism card at frontend/src/components/ui/glass-card.tsx:
1. Extend Shadcn Card with glass variant
2. Background blur effect (12-20px)
3. Semi-transparent background
4. Subtle border (white 8% opacity)
5. Hover state with glow effect
6. Optional gradient border
7. Configurable blur intensity

Variants:
- default: Standard glass effect
- elevated: Stronger shadow and lift on hover
- interactive: Scale and glow on hover
- ai: Animated gradient border for AI features

Follow Shadcn/UI extension patterns.
```

### Prompt: Create Metric Card Component

```
Create a metric display card at frontend/src/components/dashboard/MetricCard.tsx:
1. Glass card base with hover effects
2. Large value display with gradient text
3. Label text (muted color)
4. Trend indicator (up/down arrow with color)
5. Sparkline mini chart (optional)
6. Icon with accent background
7. Animated progress bar

Entrance animation: Fade up with counter animation for value.
Follow dashboard-agent patterns.
```

### Prompt: Create Feature Card Component

```
Create a feature showcase card at frontend/src/components/marketing/FeatureCard.tsx:
1. Glass card with icon header
2. Gradient icon background
3. Title and description
4. Hover lift effect with glow
5. Optional CTA link
6. Animated icon on hover
7. Stagger animation when in viewport

Use for landing page and feature highlights.
Follow react-components skill patterns.
```

---

## 🔘 Button & Interactive Element Prompts

### Prompt: Extend Button Variants

```
Extend Shadcn Button with NovaSight variants at frontend/src/components/ui/button.tsx:
1. Primary: Gradient background (indigo to purple), glow shadow
2. Secondary: Tertiary background with border hover
3. Ghost: Transparent with hover background
4. Outline: Accent border with fill on hover
5. AI: Animated gradient (purple to pink flow)
6. Destructive: Red gradient for dangerous actions
7. Icon: Square button for icon-only

All variants must include:
- Scale transform on hover (1.02) and active (0.98)
- Focus-visible ring with accent color
- Disabled state styling
- Loading spinner state

Follow Shadcn/UI cva pattern.
```

### Prompt: Create AI Action Button

```
Create an AI-specific button at frontend/src/components/ui/ai-button.tsx:
1. Animated gradient border (rotating)
2. Sparkle/stars icon animation
3. Pulsing glow effect
4. "AI" badge indicator
5. Loading state with thinking animation
6. Success state with checkmark
7. Sound effect option on click

Use for AI-powered actions (Query Assistant, AI Generate, etc.).
Follow frontend-agent specifications.
```

---

## 📝 Form Component Prompts

### Prompt: Create Styled Form Inputs

```
Extend Shadcn form inputs with NovaSight styling:
1. Update frontend/src/components/ui/input.tsx
2. Dark background (#1a1a25)
3. Border glow on focus (accent color)
4. Label animation (float up on focus/filled)
5. Error state with red border and shake animation
6. Success state with green checkmark
7. Character count for textareas
8. Icon prefix/suffix support

Follow form patterns from react-components skill.
```

### Prompt: Create Search Input Component

```
Create a styled search input at frontend/src/components/ui/search-input.tsx:
1. Glass morphism background
2. Search icon with animation
3. Clear button (appears when filled)
4. Keyboard shortcut hint
5. Loading spinner during search
6. Debounced onChange
7. Expandable variant (icon to full input)

Use for global search and filter inputs.
Follow accessibility guidelines.
```

---

## 📊 Dashboard-Specific Prompts

### Prompt: Create Dashboard Layout

```
Create the dashboard layout at frontend/src/components/layout/DashboardLayout.tsx:
1. Sidebar + main content structure
2. Responsive: sidebar sheet on mobile
3. Header integration
4. Scroll area for content
5. Grid background as page backdrop
6. Toast container positioning
7. Command palette integration

Animations:
- Content fade-in on route change
- Sidebar collapse/expand transition

Follow frontend-agent page patterns.
```

### Prompt: Create Dashboard Widget System

```
Create a dashboard widget system with:
1. frontend/src/components/dashboard/DashboardGrid.tsx (react-grid-layout)
2. frontend/src/components/dashboard/DashboardWidget.tsx (wrapper)
3. Widget header with title, menu, drag handle
4. Resize handles in edit mode
5. Widget configuration panel (sheet)
6. Add widget modal
7. Layout save/load functionality

Widget types to support: Chart, Metric, Table, Text, AI Insight
Follow dashboard-agent specifications.
```

### Prompt: Create Chart Theme

```
Configure Recharts theme for NovaSight at frontend/src/lib/chart-theme.ts:
1. Color palette array (accent colors)
2. Tooltip styling (glass effect)
3. Grid line colors (subtle)
4. Axis styling (muted text)
5. Legend styling
6. Animation configuration
7. Responsive breakpoints

Export as reusable theme object for all chart components.
Follow dashboard-agent patterns.
```

---

## 🤖 AI-Specific UI Prompts

### Prompt: Create AI Chat Interface

```
Create an AI chat component at frontend/src/components/ai/AIChatPanel.tsx:
1. Message list with user/AI distinction
2. AI typing indicator (animated dots)
3. Code block rendering with syntax highlighting
4. Copy button for code/SQL
5. Message timestamps
6. Streaming response support
7. Suggested prompts/quick actions
8. Input with submit button

Visual requirements:
- User messages: right-aligned, accent background
- AI messages: left-aligned, glass background with AI avatar
- Thinking state: pulsing dots animation

Follow ai-agent UI patterns.
```

### Prompt: Create AI Thinking Indicator

```
Create an AI processing indicator at frontend/src/components/ai/AIThinkingIndicator.tsx:
1. Spinning ring animation
2. Pulsing text "AI is analyzing..."
3. Progress steps (optional)
4. Cancel button
5. Time elapsed counter
6. Compact and expanded variants
7. Accessible aria-live region

Use accent colors with glow effect.
Follow accessibility guidelines.
```

### Prompt: Create Query Assistant UI

```
Create the Query Assistant interface at frontend/src/components/analytics/QueryAssistant.tsx:
1. Natural language input with AI button
2. Schema context selector (tables/columns)
3. Generated SQL preview with syntax highlighting
4. Edit SQL option
5. Explain query button
6. Run query action
7. History of previous queries
8. Error handling with suggestions

Integrate with AI chat panel for conversational flow.
Follow ai-agent and dashboard-agent patterns.
```

---

## ♿ Accessibility Prompts

### Prompt: Implement Focus Management

```
Implement accessibility focus management:
1. Create frontend/src/styles/focus.css with visible focus rings
2. Skip to content link
3. Focus trap for modals/dialogs
4. Roving tabindex for menus
5. Arrow key navigation for lists
6. Escape key to close overlays
7. Focus restoration after modal close

Focus ring: 2px solid accent color with 2px offset.
Follow WCAG 2.1 AA guidelines.
```

### Prompt: Add Screen Reader Support

```
Enhance components with screen reader support:
1. Proper heading hierarchy (h1-h6)
2. ARIA landmarks (main, nav, aside)
3. ARIA live regions for dynamic content
4. Descriptive alt text for images
5. Button labels for icon-only buttons
6. Form labels and error announcements
7. Loading state announcements

Test with VoiceOver and NVDA.
Follow accessibility guidelines.
```

---

## 📱 Responsive Design Prompts

### Prompt: Create Responsive Utilities

```
Set up responsive design utilities:
1. Configure breakpoints in tailwind.config.ts (sm:640, md:768, lg:1024, xl:1280, 2xl:1536)
2. Create useMediaQuery hook
3. Create useBreakpoint hook
4. Create <Show above="md"> component
5. Mobile-first CSS approach
6. Touch-friendly tap targets (44px minimum)
7. Responsive typography scale

Follow mobile-first design patterns.
```

### Prompt: Create Responsive Data Table

```
Create a responsive table at frontend/src/components/ui/responsive-table.tsx:
1. Full table on desktop
2. Card stack layout on mobile
3. Column visibility controls
4. Horizontal scroll with fade indicators
5. Sticky first column option
6. Touch-friendly row actions
7. Expandable row details

Follow react-components skill patterns.
```

---

## 🔧 Utility Prompts

### Prompt: Create Loading Skeletons

```
Create skeleton loading components:
1. frontend/src/components/ui/skeleton.tsx (base)
2. frontend/src/components/skeletons/CardSkeleton.tsx
3. frontend/src/components/skeletons/TableSkeleton.tsx
4. frontend/src/components/skeletons/ChartSkeleton.tsx
5. frontend/src/components/skeletons/FormSkeleton.tsx
6. Shimmer animation effect
7. Match actual component dimensions

Use tertiary background color with shimmer overlay.
Follow frontend-agent patterns.
```

### Prompt: Create Toast Notifications

```
Configure toast notifications with NovaSight styling:
1. Use Sonner or Shadcn Toast
2. Glass morphism background
3. Icon for type (success, error, warning, info)
4. Progress bar for timed toasts
5. Action button support
6. Stacking behavior
7. Position configuration

Entrance animation: slide in from right with fade.
Follow frontend-agent patterns.
```

### Prompt: Create Theme Toggle

```
Create a theme toggle at frontend/src/components/ui/theme-toggle.tsx:
1. Sun/Moon icon toggle
2. Smooth icon transition (rotate + fade)
3. System preference detection
4. Persist preference to localStorage
5. Apply class to document root
6. Accessible toggle button
7. Dropdown variant with system option

Follow Shadcn theme patterns.
```

---

## 📦 Page Template Prompts

### Prompt: Create Landing Page

```
Create the NovaSight landing page at frontend/src/pages/Landing.tsx:
1. Hero section with animated headline
2. Grid background with floating orbs
3. Feature cards grid (stagger animation)
4. Stats/metrics section
5. How it works steps
6. Testimonials carousel
7. CTA section with gradient button
8. Footer with links

Animations: All sections fade-up on scroll into view.
Reference Aivent website for inspiration.
Follow frontend-agent page patterns.
```

### Prompt: Create Dashboard Home Page

```
Create the dashboard home at frontend/src/pages/Dashboard/Home.tsx:
1. Welcome header with user name
2. Quick stats row (MetricCards)
3. Recent activity feed
4. Quick actions grid
5. Favorite dashboards section
6. AI insights card
7. Getting started checklist (for new users)

Entrance animations for each section.
Follow dashboard-agent and frontend-agent patterns.
```

### Prompt: Create Empty State Component

```
Create reusable empty states at frontend/src/components/ui/empty-state.tsx:
1. Illustration/icon area
2. Title and description
3. Primary action button
4. Secondary action (optional)
5. Variants for different contexts
6. Animated illustration option
7. Consistent spacing

Use for: No data, No results, Error, First-time user.
Follow react-components skill patterns.
```

---

## Usage Guide

### How to Use These Prompts

1. **Select the appropriate prompt** based on the UI component needed
2. **Replace placeholders** (text in [BRACKETS]) with actual values
3. **Reference the frontend-agent** for React/TypeScript patterns
4. **Follow the react-components skill** for component structure
5. **Verify visual design** against Aivent reference website
6. **Test accessibility** with keyboard navigation and screen readers

### Implementation Order

For a complete UI overhaul, follow this sequence:

1. Design token system and Tailwind config
2. Animation system
3. Background components
4. Layout components (Sidebar, Header)
5. Core UI components (Cards, Buttons, Inputs)
6. Page templates
7. Dashboard-specific components
8. AI interface components
9. Polish and accessibility audit

### Design Principles

| Principle | Description |
|-----------|-------------|
| **Dark-first** | Design for dark mode, adapt for light |
| **Glass morphism** | Use backdrop blur and transparency |
| **Micro-interactions** | Every action has feedback |
| **AI aesthetic** | Glows, gradients, neural patterns |
| **Accessibility** | WCAG 2.1 AA compliance minimum |
| **Performance** | Lazy load, optimize animations |

---

## Related Documents

- [Implementation Plan](../../docs/implementation/IMPLEMENTATION_PLAN.md) - Component 14: UI Redesign
- [IMPLEMENTATION_020_UI_REDESIGN.md](../../docs/implementation/IMPLEMENTATION_020_UI_REDESIGN.md) - Detailed specs
- [BRD Part 4](../../docs/requirements/BRD_Part4.md) - NFR-002: Accessibility Requirements

---

*Prompt 051 - UI Redesign & Polish v1.0*
