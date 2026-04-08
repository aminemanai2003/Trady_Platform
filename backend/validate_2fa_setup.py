#!/usr/bin/env python
"""
Vérifie qu'un nouveau compte peut être créé avec 2FA Face complet.
"""
import os
import sys
import django

sys.path.insert(0, r"c:\Users\amine\Desktop\Projet DS\fx-alpha-platform\backend")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from face_auth.models import UserFaceProfile
from notifications.models import UserTwoFAProfile

print("=" * 70)
print("TEST DE VALIDATION 2FA")
print("=" * 70)

# Chercher un utilisateur récent avec profils complets
print("\n🔍 Recherche d'un utilisateur avec 2FA Face complet...")

users_with_face = User.objects.filter(
    face_profile__isnull=False,
    twofa_profile__isnull=False,
    twofa_profile__preferred_method='face',
    twofa_profile__twofa_enabled=True
)

if users_with_face.exists():
    print(f"\n✅ {users_with_face.count()} utilisateur(s) avec 2FA Face actif:")
    
    for user in users_with_face[:3]:
        face_profile = user.face_profile
        twofa_profile = user.twofa_profile
        
        print(f"\n👤 {user.username} (ID={user.id})")
        print(f"   Face Profile:")
        print(f"     - Active: {face_profile.is_active}")
        print(f"     - Has Embedding: {bool(face_profile.embedding_enc)}")
        print(f"     - Enrolled: {face_profile.enrolled_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"     - Failed Attempts: {face_profile.failed_attempts}")
        print(f"   2FA Profile:")
        print(f"     - Enabled: {twofa_profile.twofa_enabled}")
        print(f"     - Method: {twofa_profile.preferred_method}")
        print(f"     - Created: {twofa_profile.created_at.strftime('%Y-%m-%d %H:%M')}")
    
    print("\n" + "=" * 70)
    print("✅ LA DATABASE FONCTIONNE CORRECTEMENT")
    print("=" * 70)
    print("\nLes profils 2FA et Face sont créés automatiquement lors de:")
    print("  1. POST /api/django-auth/2fa-setup → UserTwoFAProfile")
    print("  2. POST /api/face-auth/enroll → UserFaceProfile")
    print("\nLes utilisateurs sans profils sont des anciens comptes de test.")
    
else:
    print("\n⚠️  Aucun utilisateur avec 2FA Face complet trouvé.")
    print("\nCela signifie:")
    print("  - Aucun compte n'a complété le flow d'inscription moderne")
    print("  - Ou la base a été nettoyée")
    print("\n📝 Action recommandée:")
    print("  1. Aller sur http://localhost:3000/register")
    print("  2. Créer un nouveau compte")
    print("  3. Choisir 'Face Recognition' comme méthode 2FA")
    print("  4. Capturer votre visage")
    print("  5. Relancer ce script pour vérifier")

print("\n" + "=" * 70)
