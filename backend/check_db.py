import os
import sys
import django

# Setup Django
sys.path.insert(0, r"c:\Users\amine\Desktop\Projet DS\fx-alpha-platform\backend")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from face_auth.models import UserFaceProfile, FaceLivenessChallenge
from notifications.models import UserTwoFAProfile, OTPToken

# Check if tables exist (PostgreSQL)
cursor = connection.cursor()
cursor.execute("""
    SELECT tablename 
    FROM pg_catalog.pg_tables 
    WHERE schemaname = 'public' 
    ORDER BY tablename;
""")
all_tables = [table[0] for table in cursor.fetchall()]

print("=" * 60)
print("DATABASE TABLES CHECK")
print("=" * 60)

# Filter relevant tables
relevant_tables = [t for t in all_tables if any(keyword in t.lower() for keyword in ['face', 'twofa', 'otp', 'notification'])]

print("\n📋 Relevant tables found:")
for table in relevant_tables:
    print(f"  ✓ {table}")

# Check if models can query
print("\n" + "=" * 60)
print("MODEL TESTS")
print("=" * 60)

try:
    count = UserFaceProfile.objects.count()
    print(f"\n✓ UserFaceProfile: {count} records")
except Exception as e:
    print(f"\n✗ UserFaceProfile ERROR: {e}")

try:
    count = FaceLivenessChallenge.objects.count()
    print(f"✓ FaceLivenessChallenge: {count} records")
except Exception as e:
    print(f"✗ FaceLivenessChallenge ERROR: {e}")

try:
    count = UserTwoFAProfile.objects.count()
    print(f"✓ UserTwoFAProfile: {count} records")
except Exception as e:
    print(f"✗ UserTwoFAProfile ERROR: {e}")

try:
    count = OTPToken.objects.count()
    print(f"✓ OTPToken: {count} records")
except Exception as e:
    print(f"✗ OTPToken ERROR: {e}")

# Check specific user data
from django.contrib.auth.models import User

print("\n" + "=" * 60)
print("USER DATA CHECK")
print("=" * 60)

users = User.objects.all()[:5]
print(f"\n📊 Total users: {User.objects.count()}")

for user in users:
    print(f"\n👤 User: {user.username} (ID: {user.pk})")
    
    # Check face profile
    face_profile = getattr(user, 'face_profile', None)
    if face_profile:
        has_embedding = bool(face_profile.embedding_enc)
        print(f"  ✓ Face Profile: Active={face_profile.is_active}, Enrolled={face_profile.enrolled_at}, Has_Embedding={has_embedding}")
    else:
        print(f"  ✗ No Face Profile")
    
    # Check 2FA profile
    twofa_profile = getattr(user, 'twofa_profile', None)
    if twofa_profile:
        print(f"  ✓ 2FA Profile: Enabled={twofa_profile.twofa_enabled}, Method={twofa_profile.preferred_method}")
    else:
        print(f"  ✗ No 2FA Profile")

print("\n" + "=" * 60)
