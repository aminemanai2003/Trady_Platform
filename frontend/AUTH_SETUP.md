# Trady Authentication Setup

Authentication is configured through local environment variables.

Example local values:

```env
DATABASE_URL="postgresql://user:password@localhost:5432/database?schema=frontend"
NEXTAUTH_SECRET="replace-with-a-long-random-secret"
NEXTAUTH_URL="http://localhost:3000"
NEXT_PUBLIC_API_URL="http://localhost:8000/api"
GOOGLE_CLIENT_ID="replace-with-google-client-id"
GOOGLE_CLIENT_SECRET="replace-with-google-client-secret"
GITHUB_ID="replace-with-github-client-id"
GITHUB_SECRET="replace-with-github-client-secret"
```

Never commit real OAuth secrets, database passwords, or session secrets.

Supported auth features:

- Email/password login with bcrypt password hashing.
- Google OAuth when configured.
- GitHub OAuth when configured.
- Profile fields and profile picture upload.
- Optional email OTP, SMS OTP, and face authentication flows.
