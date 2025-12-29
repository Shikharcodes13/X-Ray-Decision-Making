# X-Ray Dashboard Frontend

TypeScript-based frontend for visualizing X-Ray execution data.

## Setup

```bash
npm install
npm run build
```

## Development

```bash
npm run dev  # Watch mode for development
```

## Structure

- `src/main.ts` - Application entry point
- `src/api.ts` - API client
- `src/renderer.ts` - Rendering logic
- `src/types.ts` - TypeScript type definitions
- `styles/main.css` - Styles
- `dist/` - Compiled JavaScript (generated)

## Building

The TypeScript is compiled to `dist/main.js`. Make sure to run `npm run build` before using the dashboard.

