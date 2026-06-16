# Database 2FA Diagnostic Scripts

This folder contains helper scripts for validating the 2FA and face
authentication database setup.

## Scripts

- `check_db.py`: checks PostgreSQL tables and counts 2FA/face profiles.
- `check_relationships.py`: validates OneToOne relationships between users and
  security profiles.
- `validate_2fa_setup.py`: checks that at least one face-auth-enabled account
  is configured correctly.
- `test_login_flow.py`: describes and simulates the 2FA login path for an
  existing user.
- `cleanup_old_accounts.py`: optional cleanup for old test accounts.

## Notes

- Run these scripts from the `backend` directory.
- They require the local Django environment and PostgreSQL database to be
  available.
- Do not commit real user identifiers, private embeddings, OTPs, or secrets.

Author: Team DATAMINDS
