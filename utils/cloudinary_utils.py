"""
Cloudinary helper utilities.
"""
import cloudinary
import cloudinary.uploader
from flask import current_app


def configure_cloudinary():
    """Configure Cloudinary with app credentials."""
    cloudinary.config(
        cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
        api_key=current_app.config["CLOUDINARY_API_KEY"],
        api_secret=current_app.config["CLOUDINARY_API_SECRET"],
        secure=True,
    )


def upload_image(file, folder="campusmart/products"):
    """
    Upload a single image file to Cloudinary.
    Returns a dict with 'url' and 'public_id'.
    """
    configure_cloudinary()
    try:
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            transformation=[
                {"width": 800, "height": 600, "crop": "limit", "quality": "auto"},
            ],
        )
        return {"url": result["secure_url"], "public_id": result["public_id"]}
    except Exception as e:
        raise RuntimeError(f"Cloudinary upload failed: {str(e)}")


def delete_image(public_id):
    """Delete an image from Cloudinary by its public_id."""
    configure_cloudinary()
    try:
        cloudinary.uploader.destroy(public_id)
    except Exception:
        pass  # Non-critical – log in production


def upload_multiple(files, folder="campusmart/products"):
    """Upload multiple image files and return list of {url, public_id}."""
    results = []
    for f in files:
        results.append(upload_image(f, folder=folder))
    return results
