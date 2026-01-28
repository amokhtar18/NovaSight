# Dashboard Builder UI - Installation & Setup

## Prerequisites

- Node.js 18+ and npm
- Backend API running (for full functionality)

## Installation Steps

### 1. Install Dependencies

```bash
cd frontend
npm install
```

This will install the new dependencies:
- `react-grid-layout` - Drag-and-drop grid layout
- `react-resizable` - Resizable components
- `@types/react-grid-layout` - TypeScript definitions

### 2. Verify Installation

After installation, TypeScript errors should resolve automatically.

```bash
npm run lint
npm run build
```

### 3. Start Development Server

```bash
npm run dev
```

Navigate to `http://localhost:5173/dashboards` to see the dashboard builder.

## Testing the UI

### Without Backend (UI Only)
The UI will load but API calls will fail gracefully with error states shown in widgets.

### With Backend API
Ensure these endpoints are implemented:
- `GET /api/dashboards` - List dashboards
- `POST /api/dashboards` - Create dashboard  
- `GET /api/dashboards/:id` - Get dashboard
- `PUT /api/dashboards/:id` - Update dashboard
- `DELETE /api/dashboards/:id` - Delete dashboard
- `PUT /api/dashboards/:id/layout` - Update layout
- `POST /api/dashboards/:id/widgets` - Add widget
- `GET /api/dashboards/:id/widgets/:widgetId/data` - Get widget data
- `PUT /api/dashboards/:id/widgets/:widgetId` - Update widget
- `DELETE /api/dashboards/:id/widgets/:widgetId` - Delete widget
- `GET /api/semantic/models` - Get semantic models

## Troubleshooting

### TypeScript Errors After Installation
- Run `npm install` again
- Restart VS Code TypeScript server
- Delete `node_modules` and `package-lock.json`, then `npm install`

### Grid Layout Not Working
- Ensure CSS files are imported in DashboardBuilderPage
- Check browser console for errors
- Verify react-grid-layout is installed

### Widgets Not Rendering
- Check that backend API is running
- Verify API URLs in browser Network tab
- Check authentication tokens are valid

## Next Steps

See [README.md](./README.md) for usage instructions and component documentation.
