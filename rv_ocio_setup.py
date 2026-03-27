#
# Custom OCIO setup override for OpenRV.
# Auto-configures ACES display transform and detects EXR input color spaces.
# Works with any OCIO v2 config (ACES CG, Redshift, studio configs).
#
import os
import PyOpenColorIO as OCIO


def _find_scene_linear_cs(config):
    """Get the scene-linear color space name from the config's role."""
    cs = config.getColorSpace(OCIO.ROLE_SCENE_LINEAR)
    return cs.getName() if cs else "ACEScg"


def _has_colorspace(config, name):
    """Check if a color space name exists in the active config."""
    return config.getColorSpace(name) is not None


def _match_primaries_to_config(config, attrs):
    """Match EXR chromaticity metadata to a color space in the active config.
    Returns color space name or empty string."""

    # Try named primaries first (RV metadata)
    primaries_name = attrs.get("ColorSpace/Primaries", "")
    if primaries_name:
        # Map common primaries names to candidate OCIO color space names
        # (covers both ACES CG config and Redshift config naming)
        candidates_map = {
            "aces": ["ACEScg", "ACES - ACEScg"],
            "acesp0": ["ACES2065-1"],
            "rec709": ["scene-linear Rec.709-sRGB", "Linear Rec.709 (sRGB)", "Linear sRGB"],
            "srgb": ["scene-linear Rec.709-sRGB", "Linear Rec.709 (sRGB)", "sRGB"],
            "p3": ["scene-linear DCI-P3 D65", "Linear P3-D65"],
            "rec2020": ["scene-linear Rec.2020", "Linear Rec.2020"],
        }
        pname = primaries_name.lower()
        for key, candidates in candidates_map.items():
            if key in pname:
                for cs_name in candidates:
                    if _has_colorspace(config, cs_name):
                        return cs_name
                break

    # Try matching numeric chromaticities against known primaries
    try:
        rx = float(attrs.get("ColorSpace/RedPrimary", "0,0").split(",")[0])
        ry = float(attrs.get("ColorSpace/RedPrimary", "0,0").split(",")[1])
        gx = float(attrs.get("ColorSpace/GreenPrimary", "0,0").split(",")[0])
        gy = float(attrs.get("ColorSpace/GreenPrimary", "0,0").split(",")[1])
        bx = float(attrs.get("ColorSpace/BluePrimary", "0,0").split(",")[0])
        by = float(attrs.get("ColorSpace/BluePrimary", "0,0").split(",")[1])
    except (ValueError, IndexError):
        return ""

    if rx == 0 and ry == 0:
        return ""

    measured = (round(rx, 3), round(ry, 3),
                round(gx, 3), round(gy, 3),
                round(bx, 3), round(by, 3))

    # Known primaries -> candidate color space names (checked against config)
    _KNOWN = [
        # AP1 (ACEScg)
        ((0.713, 0.293, 0.165, 0.830, 0.128, 0.044), ["ACEScg"]),
        # AP0 (ACES2065-1)
        ((0.735, 0.265, 0.000, 1.000, 0.000, -0.077), ["ACES2065-1"]),
        # Rec.709 / sRGB
        ((0.640, 0.330, 0.300, 0.600, 0.150, 0.060),
         ["scene-linear Rec.709-sRGB", "Linear Rec.709 (sRGB)"]),
        # DCI-P3 D65
        ((0.680, 0.320, 0.265, 0.690, 0.150, 0.060),
         ["scene-linear DCI-P3 D65", "Linear P3-D65"]),
        # Rec.2020
        ((0.708, 0.292, 0.170, 0.797, 0.131, 0.046),
         ["scene-linear Rec.2020", "Linear Rec.2020"]),
    ]

    for known_prims, candidates in _KNOWN:
        if all(abs(a - b) < 0.005 for a, b in zip(measured, known_prims)):
            for cs_name in candidates:
                if _has_colorspace(config, cs_name):
                    return cs_name
            break

    return ""


def ocio_config_from_media(media, attributes):
    if os.getenv("OCIO") is None:
        raise Exception("ERROR: $OCIO environment variable unset!")
    return OCIO.GetCurrentConfig()


def ocio_node_from_media(config, node, default, media=None, attributes={}):
    from rv import commands

    nodeType = commands.nodeType(node)

    if nodeType == "RVDisplayPipelineGroup":
        display = config.getDefaultDisplay()
        return [
            {
                "nodeType": "OCIODisplay",
                "context": {},
                "properties": {
                    "ocio.function": "display",
                    "ocio.inColorSpace": _find_scene_linear_cs(config),
                    "ocio_display.view": config.getDefaultView(display),
                    "ocio_display.display": display,
                },
            }
        ]

    elif nodeType == "RVLinearizePipelineGroup":
        inspace = ""

        # 1. Try filename-based detection (OCIO's built-in)
        if media:
            inspace = config.parseColorSpaceFromString(media)

        # 2. Try EXR chromaticities metadata
        if inspace == "" and attributes:
            inspace = _match_primaries_to_config(config, attributes)

        # 3. Default: float formats -> scene-linear role
        if inspace == "" and media:
            ext = os.path.splitext(media)[1].lower()
            if ext in (".exr", ".hdr", ".tx"):
                inspace = _find_scene_linear_cs(config)

        # 4. Check for explicit default_setting
        if inspace == "":
            inspace = attributes.get("default_setting", "")

        if inspace != "":
            return [
                {
                    "nodeType": "OCIOFile",
                    "context": {},
                    "properties": {
                        "ocio.function": "color",
                        "ocio.inColorSpace": inspace,
                        "ocio_color.outColorSpace": _find_scene_linear_cs(config),
                    },
                },
                {"nodeType": "RVLensWarp", "context": {}, "properties": {}},
            ]

    elif nodeType == "RVLookPipelineGroup":
        look = attributes.get("default_setting", "")
        if look != "":
            return [
                {
                    "nodeType": "OCIOLook",
                    "context": {},
                    "properties": {
                        "ocio.function": "look",
                        "ocio_look.look": look,
                    },
                }
            ]

    return [{"nodeType": d, "context": {}, "properties": {}} for d in default]
