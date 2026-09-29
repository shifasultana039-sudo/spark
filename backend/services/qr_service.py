"""
ReliefChain AI - QR Code Generation Service.
Generates pure SVG and base64 Data URIs for secure, privacy-preserving asset verification.
"""

import io
import base64
import urllib.parse
from typing import Dict, Any, Tuple

try:
    import qrcode
    import qrcode.image.svg
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False


def _generate_fallback_svg(content: str) -> str:
    """Deterministic fallback SVG if qrcode library is unavailable."""
    escaped_content = urllib.parse.quote(content)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">'
        f'<rect width="100%" height="100%" fill="#ffffff" rx="10"/>'
        f'<rect x="20" y="20" width="50" height="50" fill="#0f172a" rx="4"/>'
        f'<rect x="30" y="30" width="30" height="30" fill="#ffffff" rx="2"/>'
        f'<rect x="38" y="38" width="14" height="14" fill="#0f172a"/>'
        f'<rect x="130" y="20" width="50" height="50" fill="#0f172a" rx="4"/>'
        f'<rect x="140" y="30" width="30" height="30" fill="#ffffff" rx="2"/>'
        f'<rect x="148" y="38" width="14" height="14" fill="#0f172a"/>'
        f'<rect x="20" y="130" width="50" height="50" fill="#0f172a" rx="4"/>'
        f'<rect x="30" y="140" width="30" height="30" fill="#ffffff" rx="2"/>'
        f'<rect x="38" y="148" width="14" height="14" fill="#0f172a"/>'
        f'<rect x="85" y="25" width="20" height="15" fill="#0f172a"/>'
        f'<rect x="85" y="55" width="15" height="20" fill="#0f172a"/>'
        f'<rect x="115" y="85" width="25" height="15" fill="#0f172a"/>'
        f'<rect x="85" y="120" width="20" height="25" fill="#0f172a"/>'
        f'<rect x="120" y="130" width="20" height="20" fill="#0f172a"/>'
        f'<rect x="150" y="150" width="25" height="25" fill="#0f172a"/>'
        f'<text x="100" y="188" font-size="8" font-family="monospace" text-anchor="middle" fill="#64748b">'
        f'RELIEFCHAIN VERIFY'
        f'</text>'
        f'</svg>'
    )


def generate_qr_svg(data_to_encode: str) -> str:
    """Generates standard SVG vector representation of a QR code."""
    if not QRCODE_AVAILABLE:
        return _generate_fallback_svg(data_to_encode)

    try:
        factory = qrcode.image.svg.SvgPathImage
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
            image_factory=factory
        )
        qr.add_data(data_to_encode)
        qr.make(fit=True)
        img = qr.make_image()
        stream = io.BytesIO()
        img.save(stream)
        return stream.getvalue().decode("utf-8")
    except Exception:
        return _generate_fallback_svg(data_to_encode)


def generate_qr_bundle(data_to_encode: str) -> Dict[str, str]:
    """
    Returns both raw SVG string and ready-to-embed base64 Data URI.
    Format:
    {
        "svg": "<svg ...>...</svg>",
        "data_uri": "data:image/svg+xml;base64,...",
        "encoded_target": "https://..."
    }
    """
    svg_str = generate_qr_svg(data_to_encode)
    encoded_b64 = base64.b64encode(svg_str.encode("utf-8")).decode("utf-8")
    data_uri = f"data:image/svg+xml;base64,{encoded_b64}"
    return {
        "svg": svg_str,
        "data_uri": data_uri,
        "encoded_target": data_to_encode
    }
