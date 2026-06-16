#!/usr/bin/env python
"""
Script de nettoyage des anciens comptes de test sans profils 2FA.
Supprime les utilisateurs 1-5 qui ont été créés avant l'implémentation complète.
"""
import os
import sys
import django

sys.path.insert(0, r"c:\Users\amine\Desktop\Projet DS\fx-alpha-platform\backend")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

print("=" * 70)
print("NETTOYAGE DES ANCIENS COMPTES DE TEST")
print("=" * 70)

# Comptes de test à supprimer (créés avant 2FA)
old_test_accounts = [
    "test@example.com",
    "probe@test.com",
    "amine2faamine2fa@gmail.com",
    "amine2f11a@gmail.com",
    "aminamineaminee2fa@gmail.com",
]

print("\n🗑️  Comptes à supprimer:")
for email in old_test_accounts:
    try:
        user = User.objects.get(username=email[:150])
        print(f"  - {user.username} (ID={user.id})")
    except User.DoesNotExist:
        print(f"  - {email} (déjà supprimé)")

confirmation = input("\n⚠️  Confirmer la suppression? (oui/non): ")

if confirmation.lower() in ["oui", "yes", "y"]:
    deleted_count = 0
    for email in old_test_accounts:
        try:
            user = User.objects.get(username=email[:150])
            user_id = user.id
            username = user.username
            
            # Django cascade delete supprimera automatiquement les tokens et profils
            user.delete()
            
            print(f"  ✓ Supprimé: {username} (ID={user_id})")
            deleted_count += 1
        except User.DoesNotExist:
            continue
        except Exception as e:
            print(f"  ✗ Erreur pour {email}: {e}")
    
    print(f"\n✅ {deleted_count} compte(s) supprimé(s)")
else:
    print("\n❌ Suppression annulée")

print("\n📊 Statistiques après nettoyage:")
print(f"  Utilisateurs restants: {User.objects.count()}")
print(f"  Profils Face: {os.popen('python -c \"import django; django.setup(); from face_auth.models import UserFaceProfile; print(UserFaceProfile.objects.count())\"').read()}")
print(f"  Profils 2FA: {os.popen('python -c \"import django; django.setup(); from notifications.models import UserTwoFAProfile; print(UserTwoFAProfile.objects.count())\"').read()}")

print("\n" + "=" * 70)
