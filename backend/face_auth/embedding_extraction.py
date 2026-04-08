"""
Face embedding extraction.

The embedding is a numeric vector that uniquely encodes a face.
Backends and their embedding dimensions:
  face_recognition  → 128-d  (dlib ResNet-based)
  facenet-pytorch   → 512-d  (InceptionResnetV1 pretrained on VGGFace2)

The backend is selected automatically at runtime; models are lazily loaded
and cached as module-level globals to avoid re-loading on every request.
"""

import logging

import numpy as np

from .face_detection import FaceLocation

logger = logging.getLogger(__name__)

# ── Lazy-loaded model globals ─────────────────────────────────────────────────
_fr = None              # face_recognition module
_mtcnn = None           # facenet-pytorch MTCNN (detection/alignment)
_resnet = None          # facenet-pytorch InceptionResnetV1 (embedding)


def _load_face_recognition():
    global _fr
    if _fr is None:
        import face_recognition
        _fr = face_recognition
        logger.info("Face embedding backend: face_recognition (dlib 128-d)")
    return _fr


def _load_facenet():
    global _mtcnn, _resnet
    if _resnet is None:
        import torch
        from facenet_pytorch import MTCNN, InceptionResnetV1

        _mtcnn = MTCNN(
            keep_all=False,
            device="cpu",
            margin=20,
            min_face_size=60,
            select_largest=True,
            post_process=True,
        )
        _resnet = InceptionResnetV1(pretrained="vggface2").eval()
        logger.info("Face embedding backend: facenet-pytorch (InceptionResnetV1 512-d)")
    return _mtcnn, _resnet


# ── Public API ────────────────────────────────────────────────────────────────

def extract_embedding(img_rgb: np.ndarray, face_loc: FaceLocation | None = None) -> np.ndarray:
    """
    Extract a face embedding vector from a full RGB image.

    Args:
        img_rgb:   RGB numpy uint8 array of the full image.
        face_loc:  Optional pre-computed FaceLocation.  When provided, the
                   correct face is passed to the backend to handle multi-face
                   images (though enrollment/verification should already reject
                   images with more than one face).

    Returns:
        numpy float64 array, shape (128,) or (512,) depending on backend.

    Raises:
        ValueError:    If no encodable face is found.
        RuntimeError:  If no backend is installed.
    """
    # ── Backend 1: face_recognition ──────────────────────────────────────────
    try:
        fr = _load_face_recognition()
        known_locs = [face_loc] if face_loc is not None else None
        encodings = fr.face_encodings(img_rgb, known_face_locations=known_locs, num_jitters=1)
        if not encodings:
            raise ValueError("No encodable face found (face_recognition).")
        return np.array(encodings[0], dtype=np.float64)
    except ImportError:
        pass

    # ── Backend 2: facenet-pytorch ────────────────────────────────────────────
    try:
        import torch
        from PIL import Image

        mtcnn, resnet = _load_facenet()
        pil = Image.fromarray(img_rgb)

        # If face_loc is provided, crop manually before MTCNN alignment
        if face_loc is not None:
            pad = 20
            t = max(0, face_loc.top - pad)
            b = min(img_rgb.shape[0], face_loc.bottom + pad)
            l = max(0, face_loc.left - pad)
            r = min(img_rgb.shape[1], face_loc.right + pad)
            pil = Image.fromarray(img_rgb[t:b, l:r])

        face_tensor = mtcnn(pil)
        if face_tensor is None:
            raise ValueError("No alignable face found (facenet-pytorch MTCNN).")

        with torch.no_grad():
            emb = resnet(face_tensor.unsqueeze(0)).squeeze(0)
        return emb.numpy().astype(np.float64)
    except ImportError:
        pass

    raise RuntimeError(
        "No face embedding backend available. Install one:\n"
        "  Option A (easier on Windows): pip install facenet-pytorch\n"
        "  Option B: pip install cmake dlib face_recognition"
    )


def get_landmarks(img_rgb: np.ndarray) -> dict | None:
    """
    Return facial landmark points for liveness detection.

    Returns dict with keys 'left_eye', 'right_eye' (lists of (x, y) tuples),
    or None if landmarks are unavailable.

    face_recognition returns 68-point landmarks (full eyes for EAR).
    facenet-pytorch MTCNN returns 5-point landmarks (eye centres only).
    """
    # ── face_recognition: full 68-point landmarks ─────────────────────────────
    try:
        fr = _load_face_recognition()
        lm_list = fr.face_landmarks(img_rgb)
        if lm_list:
            # face_recognition returns left_eye / right_eye as lists of 6 pts each
            return lm_list[0]
        return None
    except ImportError:
        pass

    # ── facenet-pytorch MTCNN: 5-point landmarks (eye centres) ────────────────
    try:
        import numpy as _np
        from PIL import Image
        from facenet_pytorch import MTCNN as _MTCNN

        _lm_mtcnn = _MTCNN(keep_all=False, device="cpu", select_largest=True)
        pil = Image.fromarray(img_rgb)
        boxes, probs, points = _lm_mtcnn.detect(pil, landmarks=True)
        if points is None or len(points) == 0:
            return None
        kp = points[0]  # shape (5, 2): left_eye, right_eye, nose, mouth_l, mouth_r
        return {
            "left_eye":  [tuple(kp[0].tolist())],
            "right_eye": [tuple(kp[1].tolist())],
            "nose_tip":  [tuple(kp[2].tolist())],
        }
    except (ImportError, Exception):
        pass

    return None
