import os
import sys
import django

# Setup Django
sys.path.insert(0, r"c:\Users\amine\Desktop\Projet DS\fx-alpha-platform\backend")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from face_auth.models import UserFaceProfile
from notifications.models import UserTwoFAProfile

print("=" * 70)
print("DETAILED RELATIONSHIP CHECK")
print("=" * 70)

# Show all face profiles with their user IDs
print("\n📷 FACE PROFILES IN DATABASE:")
face_profiles = UserFaceProfile.objects.all()
for fp in face_profiles:
    has_embedding = bool(fp.embedding_enc)
    print(f"  ID={fp.id}, user_id={fp.user_id}, username={fp.user.username}, has_embedding={has_embedding}")

# Show all 2FA profiles with their user IDs
print("\n🔐 2FA PROFILES IN DATABASE:")
twofa_profiles = UserTwoFAProfile.objects.all()
for tp in twofa_profiles:
    print(f"  ID={tp.id}, user_id={tp.user_id}, username={tp.user.username}, enabled={tp.twofa_enabled}, method={tp.preferred_method}")

# Now check if we can access them from User side
print("\n👥 USER → PROFILE MAPPING:")
for user in User.objects.all()[:10]:
    print(f"\n  User ID={user.id}, username={user.username}")
    
    # Try direct query
    face_direct = UserFaceProfile.objects.filter(user_id=user.id).first()
    twofa_direct = UserTwoFAProfile.objects.filter(user_id=user.id).first()
    
    print(f"    Direct query - Face: {'✓' if face_direct else '✗'}, 2FA: {'✓' if twofa_direct else '✗'}")
    
    # Try related name
    try:
        face_related = user.face_profile
        print(f"    user.face_profile: ✓ (ID={face_related.id})")
    except Exception as e:
        print(f"    user.face_profile: ✗ ({type(e).__name__})")
    
    try:
        twofa_related = user.twofa_profile
        print(f"    user.twofa_profile: ✓ (ID={twofa_related.id})")
    except Exception as e:
        print(f"    user.twofa_profile: ✗ ({type(e).__name__})")

print("\n" + "=" * 70)
