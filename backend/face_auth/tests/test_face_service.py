"""
Unit / integration tests for face_auth.face_service and face_auth.validation.

Run with:
    python manage.py test face_auth.tests.test_face_service
"""

import base64
import io
import math
import struct
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

# ---------------------------------------------------------------------------
# Helpers to build synthetic images
# ---------------------------------------------------------------------------

def _blank_rgb(w: int = 120, h: int = 120, fill: int = 128) -> np.ndarray:
    """Return an H×W×3 uint8 BGR array filled with a uniform grey."""
    return np.full((h, w, 3), fill, dtype=np.uint8)


def _as_b64_jpeg(arr: np.ndarray) -> str:
    """Encode a numpy array as a base64 JPEG string (requires opencv)."""
    import cv2  # noqa: F401 — only needed at test time
    ok, buf = cv2.imencode(".jpg", arr)
    assert ok
    return base64.b64encode(buf.tobytes()).decode()


def _as_b64_png(arr: np.ndarray) -> str:
    import cv2
    ok, buf = cv2.imencode(".png", arr)
    assert ok
    return base64.b64encode(buf.tobytes()).decode()


def _corrupted_b64() -> str:
    """Return a base64 string that is not a valid image."""
    return base64.b64encode(b"\x00\x01\x02corrupt").decode()


def _gif_b64() -> str:
    """Return a base64 string with a GIF magic header."""
    return base64.b64encode(b"GIF89a\x00").decode()


# ---------------------------------------------------------------------------
# face_service tests (DeepFace mocked)
# ---------------------------------------------------------------------------

class TestDecodeImage(unittest.TestCase):
    def test_numpy_passthrough(self):
        from face_auth.face_service import decode_image
        arr = _blank_rgb()
        result = decode_image(arr)
        np.testing.assert_array_equal(result, arr)

    def test_base64_jpeg_roundtrip(self):
        from face_auth.face_service import decode_image
        arr = _blank_rgb(fill=200)
        b64 = _as_b64_jpeg(arr)
        decoded = decode_image(b64)
        self.assertEqual(decoded.shape[2], 3)
        self.assertEqual(decoded.dtype, np.uint8)

    def test_invalid_base64_raises(self):
        from face_auth.face_service import decode_image
        with self.assertRaises(ValueError):
            decode_image("not-valid-base64!!")

    def test_corrupted_bytes_raises(self):
        from face_auth.face_service import decode_image
        with self.assertRaises(ValueError):
            decode_image(_corrupted_b64())


class TestDetectAndValidate(unittest.TestCase):
    """Mock DeepFace so tests never load GPU models."""

    def _make_face_region(self, w=120, h=120):
        return {"x": 0, "y": 0, "w": w, "h": h}

    @patch("face_auth.face_service.DeepFace")
    def test_valid_single_face(self, MockDF):
        from face_auth.face_service import detect_and_validate

        face_img = _blank_rgb(fill=180)
        MockDF.extract_faces.return_value = [
            {"face": face_img, "facial_area": self._make_face_region(), "confidence": 0.99}
        ]
        MockDF.represent.return_value = [{"embedding": [0.1] * 512}]

        result = detect_and_validate(_blank_rgb())
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["embedding"]), 512)

    @patch("face_auth.face_service.DeepFace")
    def test_no_face(self, MockDF):
        from face_auth.face_service import detect_and_validate

        MockDF.extract_faces.return_value = []

        result = detect_and_validate(_blank_rgb())
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "no_face")

    @patch("face_auth.face_service.DeepFace")
    def test_multiple_faces(self, MockDF):
        from face_auth.face_service import detect_and_validate

        fake_face = _blank_rgb(fill=180)
        MockDF.extract_faces.return_value = [
            {"face": fake_face, "facial_area": self._make_face_region(), "confidence": 0.99},
            {"face": fake_face, "facial_area": self._make_face_region(), "confidence": 0.95},
        ]

        result = detect_and_validate(_blank_rgb())
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "multiple_faces")

    @patch("face_auth.face_service.DeepFace")
    def test_deepface_exception_returns_system_error(self, MockDF):
        from face_auth.face_service import detect_and_validate

        MockDF.extract_faces.side_effect = RuntimeError("GPU OOM")

        result = detect_and_validate(_blank_rgb())
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "system_error")


class TestVerifyFaces(unittest.TestCase):

    def _unit_vec(self, dim=512, index=0):
        v = [0.0] * dim
        v[index] = 1.0
        return v

    @patch("face_auth.face_service.DeepFace")
    def test_same_embedding_verified(self, MockDF):
        from face_auth.face_service import verify_faces

        emb = [0.1] * 512
        face_img = _blank_rgb(fill=180)
        MockDF.extract_faces.return_value = [
            {"face": face_img, "facial_area": {"x": 0, "y": 0, "w": 120, "h": 120}, "confidence": 0.99}
        ]
        MockDF.represent.return_value = [{"embedding": emb}]

        result = verify_faces(emb, emb)
        self.assertTrue(result["verified"])
        self.assertAlmostEqual(result["distance"], 0.0, places=5)
        self.assertAlmostEqual(result["confidence"], 1.0, places=5)

    @patch("face_auth.face_service.DeepFace")
    def test_orthogonal_embeddings_not_verified(self, MockDF):
        from face_auth.face_service import verify_faces

        stored = self._unit_vec(index=0)
        live   = self._unit_vec(index=1)   # orthogonal → distance = 1.0

        face_img = _blank_rgb(fill=180)
        MockDF.extract_faces.return_value = [
            {"face": face_img, "facial_area": {"x": 0, "y": 0, "w": 120, "h": 120}, "confidence": 0.99}
        ]
        MockDF.represent.return_value = [{"embedding": live}]

        result = verify_faces(stored, live)
        self.assertFalse(result["verified"])
        self.assertGreater(result["distance"], 0.39)

    @patch("face_auth.face_service.DeepFace")
    def test_no_face_in_live_image(self, MockDF):
        from face_auth.face_service import verify_faces

        MockDF.extract_faces.return_value = []

        result = verify_faces([0.1] * 512, _blank_rgb())
        self.assertFalse(result["verified"])
        self.assertEqual(result["reason"], "no_face")


class TestCosineDistance(unittest.TestCase):

    def test_identical_vectors(self):
        from face_auth.face_service import _cosine_distance
        a = [1.0, 0.0, 0.0]
        self.assertAlmostEqual(_cosine_distance(a, a), 0.0, places=10)

    def test_opposite_vectors(self):
        from face_auth.face_service import _cosine_distance
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        self.assertAlmostEqual(_cosine_distance(a, b), 2.0, places=10)

    def test_orthogonal_vectors(self):
        from face_auth.face_service import _cosine_distance
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        self.assertAlmostEqual(_cosine_distance(a, b), 1.0, places=10)

    def test_zero_vector_returns_1(self):
        from face_auth.face_service import _cosine_distance
        # numerically degenerate; must not raise
        result = _cosine_distance([0.0, 0.0], [1.0, 0.0])
        self.assertFalse(math.isnan(result))


# ---------------------------------------------------------------------------
# validation.py tests
# ---------------------------------------------------------------------------

class TestValidateImageInput(unittest.TestCase):

    def test_valid_jpeg(self):
        from face_auth.validation import validate_image_input
        b64 = _as_b64_jpeg(_blank_rgb())
        result = validate_image_input(b64)
        self.assertTrue(result["valid"])

    def test_valid_png(self):
        from face_auth.validation import validate_image_input
        b64 = _as_b64_png(_blank_rgb())
        result = validate_image_input(b64)
        self.assertTrue(result["valid"])

    def test_rejects_gif(self):
        from face_auth.validation import validate_image_input
        result = validate_image_input(_gif_b64())
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "invalid_image")

    def test_rejects_corrupt_bytes(self):
        from face_auth.validation import validate_image_input
        result = validate_image_input(_corrupted_b64())
        self.assertFalse(result["valid"])

    def test_rejects_non_string(self):
        from face_auth.validation import validate_image_input
        result = validate_image_input(12345)
        self.assertFalse(result["valid"])

    def test_rejects_oversized(self):
        from face_auth.validation import validate_image_input
        # Build ~5 MB base64 payload (exceeds 4 MB limit)
        big = base64.b64encode(b"\xff\xd8\xff" + b"\x00" * (5 * 1024 * 1024)).decode()
        result = validate_image_input(big)
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "invalid_image")


class TestValidateEnrollRequest(unittest.TestCase):

    def test_valid_payload(self):
        from face_auth.validation import validate_enroll_request
        b64 = _as_b64_jpeg(_blank_rgb())
        result = validate_enroll_request({"image": b64})
        self.assertTrue(result["valid"])
        self.assertEqual(result["image"], b64)

    def test_missing_image_key(self):
        from face_auth.validation import validate_enroll_request
        result = validate_enroll_request({})
        self.assertFalse(result["valid"])

    def test_none_data(self):
        from face_auth.validation import validate_enroll_request
        result = validate_enroll_request(None)
        self.assertFalse(result["valid"])


class TestValidateVerifyRequest(unittest.TestCase):

    def test_valid_minimal(self):
        from face_auth.validation import validate_verify_request
        b64 = _as_b64_jpeg(_blank_rgb())
        result = validate_verify_request({"image": b64})
        self.assertTrue(result["valid"])

    def test_valid_with_challenge(self):
        from face_auth.validation import validate_verify_request
        b64 = _as_b64_jpeg(_blank_rgb())
        result = validate_verify_request({
            "image": b64,
            "challenge_id": "550e8400-e29b-41d4-a716-446655440000",
            "liveness_frame": b64,
        })
        self.assertTrue(result["valid"])

    def test_missing_image(self):
        from face_auth.validation import validate_verify_request
        result = validate_verify_request({"challenge_id": "abc"})
        self.assertFalse(result["valid"])


# ---------------------------------------------------------------------------
# Integration: enroll → verify round-trip (mocked DeepFace + DB)
# ---------------------------------------------------------------------------

class TestEnrollAndVerifyIntegration(unittest.TestCase):
    """
    Smoke test for auth_integration.enroll_face + verify_face.
    All DeepFace calls and ORM calls are mocked.
    """

    def _make_user(self):
        user = MagicMock()
        user.pk = 1
        user.username = "alice"
        user.email = "alice@example.com"
        return user

    @patch("face_auth.auth_integration.detect_and_validate")
    @patch("face_auth.auth_integration.UserFaceProfile")
    @patch("face_auth.auth_integration._activate_face_2fa")
    def test_enroll_success(self, mock_activate, MockProfile, mock_detect):
        from face_auth.auth_integration import enroll_face

        mock_detect.return_value = {"ok": True, "embedding": [0.1] * 512}
        mock_profile_instance = MagicMock()
        MockProfile.objects.update_or_create.return_value = (mock_profile_instance, True)

        b64 = _as_b64_jpeg(_blank_rgb())
        result = enroll_face(self._make_user(), b64)
        self.assertTrue(result["ok"])
        self.assertTrue(result["created"])

    @patch("face_auth.auth_integration.detect_and_validate")
    @patch("face_auth.auth_integration.UserFaceProfile")
    @patch("face_auth.auth_integration._activate_face_2fa")
    def test_enroll_no_face(self, mock_activate, MockProfile, mock_detect):
        from face_auth.auth_integration import enroll_face

        mock_detect.return_value = {"ok": False, "reason": "no_face", "detail": "nothing"}

        b64 = _as_b64_jpeg(_blank_rgb())
        result = enroll_face(self._make_user(), b64)
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "no_face")

    @patch("face_auth.auth_integration.verify_faces")
    @patch("face_auth.auth_integration.decrypt_embedding")
    def test_verify_match(self, mock_decrypt, mock_verify):
        from face_auth.auth_integration import verify_face

        emb = [0.1] * 512
        mock_decrypt.return_value = emb
        mock_verify.return_value = {
            "verified": True, "confidence": 0.97,
            "distance": 0.03, "reason": "match", "detail": "",
        }

        user = self._make_user()
        profile = MagicMock()
        profile.is_active = True
        profile.embedding_enc = b"encrypted"
        profile.failed_attempts = 0
        user.face_profile = profile

        b64 = _as_b64_jpeg(_blank_rgb())
        result = verify_face(user, b64)
        self.assertTrue(result["verified"])
        self.assertAlmostEqual(result["confidence"], 0.97)

    @patch("face_auth.auth_integration.verify_faces")
    @patch("face_auth.auth_integration.decrypt_embedding")
    def test_verify_nonmatch(self, mock_decrypt, mock_verify):
        from face_auth.auth_integration import verify_face

        emb = [0.1] * 512
        mock_decrypt.return_value = emb
        mock_verify.return_value = {
            "verified": False, "confidence": 0.2,
            "distance": 0.8, "reason": "no_match", "detail": "distance too high",
        }

        user = self._make_user()
        profile = MagicMock()
        profile.is_active = True
        profile.embedding_enc = b"encrypted"
        profile.failed_attempts = 0
        user.face_profile = profile

        b64 = _as_b64_jpeg(_blank_rgb())
        result = verify_face(user, b64)
        self.assertFalse(result["verified"])
        self.assertTrue(result.get("fallback_available", False))

    def test_verify_no_profile(self):
        from face_auth.auth_integration import verify_face

        user = self._make_user()
        del user.face_profile  # simulate missing attribute

        # getattr with default None
        user.face_profile = None

        b64 = _as_b64_jpeg(_blank_rgb())
        result = verify_face(user, b64)
        self.assertFalse(result["verified"])
        self.assertEqual(result["reason"], "no_enrollment")

    def test_verify_locked_account(self):
        from face_auth.auth_integration import verify_face

        user = self._make_user()
        profile = MagicMock()
        profile.is_active = True
        profile.embedding_enc = b"encrypted"
        profile.failed_attempts = 5   # at max
        user.face_profile = profile

        b64 = _as_b64_jpeg(_blank_rgb())
        result = verify_face(user, b64)
        self.assertFalse(result["verified"])
        self.assertEqual(result["reason"], "locked")


if __name__ == "__main__":
    unittest.main()
