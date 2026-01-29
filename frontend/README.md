# DCNC Frontend - Multi-Tenant Data Quality Dashboard

Modern React-based frontend for the DCNC Data Quality API with multi-tenant support.

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm/yarn
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 📁 Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── components/      # Reusable components
│   ├── pages/          # Page components
│   ├── services/       # API services
│   ├── store/          # State management
│   ├── hooks/          # Custom hooks
│   ├── utils/          # Utilities
│   └── types/          # TypeScript types
└── package.json
```

## 🔧 Environment Variables

Create `.env` file:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_APP_NAME=DCNC Data Quality
```

## 📦 Tech Stack

- **React 18+** with TypeScript
- **Vite** - Build tool
- **Material-UI (MUI)** - UI components
- **Redux Toolkit** - State management
- **React Router** - Routing
- **Axios** - HTTP client
- **Recharts** - Charts
- **React Hook Form** - Forms

## 🎨 Features

- ✅ Multi-tenant authentication
- ✅ Interactive dashboard
- ✅ File upload (drag & drop)
- ✅ Real-time job status
- ✅ Classification & Correction workflows
- ✅ Results visualization
- ✅ Job history & management
- ✅ Client-specific data isolation

## 📝 Development

```bash
# Run linter
npm run lint

# Run type check
npm run type-check

# Run tests
npm run test
```

## 🚢 Deployment

```bash
# Build for production
npm run build

# Output will be in dist/ folder
# Deploy to your hosting service (Vercel, Netlify, etc.)
```
