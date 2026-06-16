# Testing 2FA Verification After Registration

## Prerequisites

### 1. Start Django Backend
```powershell
cd "c:\Users\amine\Desktop\Projet DS\fx-alpha-platform\backend"
& "c:/Users/amine/Desktop/Projet DS/.venv/Scripts/python.exe" manage.py runserver
```

The backend MUST be running on `http://localhost:8000` for face verification to work.

### 2. Start Next.js Frontend
```powershell
cd "c:\Users\amine\Desktop\Projet DS\fx-alpha-platform\frontend"
npm run dev
```

Frontend will be available on `http://localhost:3000`

---

## Testing Face ID Verification Flow

### Step 1: Register New Account
1. Navigate to `http://localhost:3000/register`
2. Fill in:
   - Name
   - Email
   - Password (min 6 characters)
3. Upload ID card image
4. Click "Scan and extract"
5. Confirm extracted data
6. Click "Create account"

### Step 2: Choose Face ID 2FA
1. After successful registration, you'll see "Secure your account" page
2. Click on "Face ID" option
3. Click "Open camera to enroll"

### Step 3: Face Enrollment
1. FaceEnrollModal opens with camera preview
2. Center your face in the oval guide
3. Click "Capture & enroll"
4. Wait 10-30 seconds (first time may download AI models)
5. Success message appears

### Step 4: Face Verification (NEW)
1. After enrollment, you'll see "Verify face setup" page
2. Camera opens again automatically
3. Click "Capture & verify"
4. Wait 10-30 seconds for AI verification
5. ✅ Success: "Face verified!" → Redirects to dashboard
6. ❌ Failed: Error message with "Try again" button

### Step 5: Skip Option
- At any verification step, click "Skip for now" to go directly to dashboard without verifying

---

## Common Issues & Solutions

### Issue: "Network error during verification"

**Causes:**
1. ❌ Django backend is not running
2. ❌ Backend is on different port than `http://localhost:8000`
3. ❌ Network timeout (AI model loading)

**Solutions:**
1. ✅ Check Django terminal - should show `Starting development server at http://127.0.0.1:8000/`
2. ✅ Verify `DJANGO_API_URL` in frontend `.env.local` is set correctly
3. ✅ Wait 30 seconds and click "Try again" (AI model is downloading)

### Issue: "Face verification failed"

**Causes:**
1. Poor lighting conditions
2. Multiple faces in frame
3. Face not matching enrollment
4. Face too small or blurry

**Solutions:**
1. Ensure good lighting (face clearly visible)
2. Remove other people from camera view
3. Try enrolling again with better image quality
4. Move closer to camera (face should fill the oval guide)

### Issue: "Camera access denied"

**Solution:**
- Allow camera permissions in browser settings
- Chrome: `chrome://settings/content/camera`
- Edge: `edge://settings/content/camera`

---

## Timeout Settings

- **Client-side timeout**: 120 seconds (2 minutes)
- **Backend timeout**: 120 seconds (configured in route)
- **First-time AI model download**: ~30-90 seconds

If verification takes longer than 2 minutes, you'll see:
> "The AI model is still loading. Please wait 30 seconds and try again."

---

## Testing Email/SMS Verification

### Email OTP
1. Choose "Email OTP" during 2FA setup
2. Check your email for 6-digit code
3. Enter code in verification page
4. Click "Verify code"

### SMS OTP
1. Choose "SMS OTP" during 2FA setup
2. Enter phone number in E.164 format (e.g., `+33612345678`)
3. Check your phone for SMS with 6-digit code
4. Enter code in verification page
5. Click "Verify code"

---

## Debugging

### Check Django Logs
```powershell
# In backend terminal, look for:
"2FA setup test (face) success | user_id=X confidence=0.XX"
# OR
"2FA setup test (face) failed | user_id=X reason=no_match"
```

### Check Browser Console
```javascript
// Open DevTools (F12) → Console
// Look for fetch errors or AbortError
```

### Check Backend is Reachable
```powershell
curl http://localhost:8000/api/auth/2fa/setup/
# Should return: {"detail":"Authentication credentials were not provided."}
```

---

## Success Criteria

✅ User can register account  
✅ User can choose Face ID 2FA method  
✅ User can enroll face successfully  
✅ User is redirected to verification page after enrollment  
✅ User can verify face successfully within 2 minutes  
✅ User is redirected to dashboard after successful verification  
✅ User can skip verification and still access dashboard  

---

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/register` | POST | NextAuth registration |
| `/api/django-auth/django-register` | POST | Django user creation + token |
| `/api/django-auth/2fa-setup` | POST | Enable 2FA method |
| `/api/face-auth/enroll` | POST | Face enrollment (DeepFace) |
| `/api/django-auth/verify-2fa-setup` | POST | Verify 2FA setup |
| `/api/django-auth/send-otp` | POST | Send OTP for email/SMS |

---

## Notes

- Face verification uses **simple capture** (no liveness detection) as requested
- DeepFace model (ArcFace) is ~100MB and downloads on first use
- Embeddings are encrypted with Fernet (AES-128-CBC) before storage
- Threshold for face match: cosine distance < 0.40
- Rate limits: 5 verification attempts per 10 minutes
