from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from pathlib import Path
from typing import Dict, Any

def _get_if_exist(data, key):
    if key in data:
        return data[key]
    return None

def _convert_to_degrees(value):
    """Helper to convert GPS coordinates to degrees"""
    d = float(value[0])
    m = float(value[1])
    s = float(value[2])
    return d + (m / 60.0) + (s / 3600.0)

def extract_exif(image_path: Path) -> str:
    """Extract relevant EXIF data from a JPEG image and return a formatted string."""
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if not exif_data:
            return ""
        exif = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            exif[tag] = value

        # Extract GPS if available
        gps_info = exif.get("GPSInfo")
        gps_str = ""
        if gps_info:
            gps = {}
            for key in gps_info.keys():
                decode = GPSTAGS.get(key, key)
                gps[decode] = gps_info[key]
            if "GPSLatitude" in gps and "GPSLatitudeRef" in gps and "GPSLongitude" in gps and "GPSLongitudeRef" in gps:
                lat = _convert_to_degrees(gps["GPSLatitude"])
                if gps["GPSLatitudeRef"] != "N":
                    lat = -lat
                lon = _convert_to_degrees(gps["GPSLongitude"])
                if gps["GPSLongitudeRef"] != "E":
                    lon = -lon
                gps_str = f"GPS: {lat:.4f}° {gps['GPSLatitudeRef']}, {lon:.4f}° {gps['GPSLongitudeRef']}"

        # Build output
        parts = []
        if "Make" in exif and "Model" in exif:
            parts.append(f"Camera: {exif['Make']} {exif['Model']}")
        elif "Model" in exif:
            parts.append(f"Camera: {exif['Model']}")
        if "LensModel" in exif:
            parts.append(f"Lens: {exif['LensModel']}")
        if "FNumber" in exif:
            parts.append(f"Aperture: f/{exif['FNumber']:.1f}")
        if "ExposureTime" in exif:
            parts.append(f"Shutter: {exif['ExposureTime']}s")
        if "ISOSpeedRatings" in exif:
            parts.append(f"ISO: {exif['ISOSpeedRatings']}")
        if "DateTimeOriginal" in exif:
            parts.append(f"Date: {exif['DateTimeOriginal']}")
        if gps_str:
            parts.append(gps_str)

        return ", ".join(parts)
    except Exception:
        return ""
