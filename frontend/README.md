# Trady Frontend

Frontend application for the FX Alpha Platform (Team DATAMINDS), built with Next.js 16 and React 19.

## Overview

This app provides:

- A modern animated landing page for Trady
- Authentication flow (login/register)
- Dashboard modules for trading, analytics, monitoring, reports, agents, and settings
- API integration with the Django backend at port 8000

The landing page currently includes ReactBits animations:

- Light Pillar background effect
- Splash Cursor fluid interaction

Both are integrated in English-only UI copy and aligned with the product color palette.

## Tech Stack

- Next.js 16 (App Router)
- React 19
- TypeScript
- Tailwind CSS 4
- shadcn/ui primitives
- Motion/Framer Motion
- NextAuth
- Prisma
- TanStack Query

## Main Routes

- `/` Landing page
- `/login` Login
- `/register` Register
- `/dashboard` Dashboard home
- `/trading` Trading page
- `/analytics` Analytics page
- `/monitoring` Monitoring page
- `/reports` Reports page
- `/agents` Agents page
- `/settings` Settings page
- `/backtesting` Backtesting page
- `/features` Features page

## Project Structure

```text
frontend/
	src/
		app/
			page.tsx                # Landing page
			(auth)/                 # Auth pages
			(dashboard)/            # Dashboard pages
			api/                    # Next.js API routes
		components/
			ui/                     # UI primitives
			LightPillar.jsx         # ReactBits light pillar animation
			SplashCursor.jsx        # ReactBits splash cursor animation
		lib/
			api.ts                  # API client helpers
			auth.ts                 # Auth helpers
			prisma.ts               # Prisma client
		types/
			index.ts                # Shared frontend types
```

## Getting Started

### Prerequisites

- Node.js 18+
- npm 9+

### Installation

```bash
cd fx-alpha-platform/frontend
npm install
```

### Development

```bash
npm run dev
```

Open http://localhost:3000.

## Build and Run

```bash
npm run build
npm run start
```

## Scripts

- `npm run dev` Start development server
- `npm run build` Create production build
- `npm run start` Start production server
- `npm run lint` Run ESLint

## Backend Integration

The frontend expects the backend API to be available at `http://localhost:8000`.

Recommended startup order for local development:

1. Start infrastructure with Docker from repository root.
2. Start Django backend on port 8000.
3. Start frontend on port 3000.

## Notes

- This project uses App Router route groups for organization.
- Keep all user-facing text in English for consistency.
- Landing animation components are intentionally loaded only on the landing page.
- ID verification uses a Gemini vision parser when `GEMINI_API_KEY` is available.
