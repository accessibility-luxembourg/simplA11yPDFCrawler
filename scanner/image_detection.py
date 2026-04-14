from __future__ import annotations


def detect_image_objects(pdf) -> dict[str, int]:
    """
    Detect simple image XObjects on each page.

    This is intentionally lightweight for Phase 1:
    - inspect each page's /Resources
    - inspect /XObject
    - count entries whose /Subtype is /Image

    Returns:
        {
            "ImageObjectsFound": int,
            "PagesWithImages": int,
        }
    """
    image_objects_found = 0
    pages_with_images = 0

    for page in pdf.pages:
        page_has_image = False

        try:
            resources = page.get("/Resources")
            if resources is None:
                continue

            xobjects = resources.get("/XObject")
            if xobjects is None:
                continue

            for key in xobjects:
                try:
                    xobj = xobjects[key]
                    if str(xobj.get("/Subtype")) == "/Image":
                        image_objects_found += 1
                        page_has_image = True
                except Exception:
                    continue

            if page_has_image:
                pages_with_images += 1

        except Exception:
            continue

    return {
        "ImageObjectsFound": image_objects_found,
        "PagesWithImages": pages_with_images,
    }
