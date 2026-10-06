# DevAgents Web UI

This is the Web UI for the DevAgents research platform.

## Architecture

- **Frontend**: React, Vite, TailwindCSS, TypeScript
- **Backend API**: FastAPI (Python)
- **State Management**: React Router, standard React hooks
- **Updates**: Controlled polling to the backend API telemetry events

## How to run

1. Install backend dependencies (if not already installed):
```bash
cd ..
pip install fastapi uvicorn
```

2. Start the backend API (from the root directory):
```bash
python -m uvicorn api.main:app --reload
```

3. Start the frontend development server:
```bash
cd ui
npm install
npm run dev
```

4. Navigate to `http://localhost:5173` to view the dashboard.

## Security

The Web UI does not have direct access to the local filesystem or `.env` secrets. All data is served through the FastAPI backend layer which sanitizes all telemetry.
