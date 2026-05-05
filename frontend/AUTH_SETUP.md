# Trady - Authentication Setup ✅

## Configuration Complète

### 1. Base de données MySQL
- ✅ Base de données: `fx_alpha` créée
- ✅ Tables Prisma synchronisées (User, UserSettings, Position, Order, Signal)
- ✅ Prisma Client généré

### 2. Variables d'environnement (.env)
```env
DATABASE_URL="mysql://root:@localhost:3306/fx_alpha"
NEXTAUTH_SECRET="fx-alpha-super-secret-key-change-in-production"
NEXTAUTH_URL="http://localhost:3000"
NEXT_PUBLIC_API_URL="http://localhost:8000/api"
```

### 3. Fonctionnalités d'authentification

#### Pages disponibles:
- `/login` - Connexion utilisateur
- `/register` - Inscription utilisateur
- `/` - Landing page publique
- `/dashboard` - Dashboard protégé (nécessite authentification)

#### Routes protégées:
- `/dashboard/*`
- `/agents/*`
- `/analytics/*`
- `/reports/*`
- `/trading/*`
- `/monitoring/*`
- `/settings/*`

### 4. Palette de couleurs Trady

**Couleurs principales:**
- Yale Blue (fond): `#183D53`
- Fern (vert): `#4D8048`
- Sapphire (bleu): `#0658BA`
- Black: `#000000`

### 5. Comment tester

#### Démarrer le serveur:
```bash
cd frontend
npm run dev
```

Le serveur démarre sur http://localhost:3000 (ou 3001 si le port 3000 est occupé)

#### Créer un compte:
1. Aller sur http://localhost:3000/register
2. Remplir le formulaire (nom, email, mot de passe min 6 caractères)
3. Cliquer sur "Create Account"
4. Vous serez automatiquement connecté et redirigé vers le dashboard

#### Se connecter:
1. Aller sur http://localhost:3000/login
2. Entrer email et mot de passe
3. Cliquer sur "Sign In"

### 6. Structure de la base de données

**Table User:**
- id (cuid)
- name
- email (unique)
- hashedPassword (bcrypt, rounds=12)
- createdAt
- updatedAt

**Table UserSettings:**
- Paramètres de trading par défaut
- Notifications
- Gestion des risques

### 7. Sécurité

- ✅ Mots de passe hashés avec bcrypt
- ✅ Sessions JWT avec NextAuth
- ✅ Middleware de protection des routes
- ✅ CSRF protection
- ✅ Validation des données côté serveur

## Notes importantes

1. **MySQL doit être en cours d'exécution** sur localhost:3306
2. La base `fx_alpha` doit exister
3. Pour réinitialiser la BDD: `npx prisma db push --force-reset`
4. Pour voir les données: `npx prisma studio`

## Prochaines étapes

- [ ] Intégration avec le backend Django
- [ ] Ajouter OAuth (Google, GitHub)
- [ ] Email verification
- [ ] Password reset
- [ ] 2FA (Two-Factor Authentication)
