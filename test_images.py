"""Standalone test script for testing product images.

Processes images from the productimage folder and generates PDF reports.
Usage: python test_images.py
"""

import sys
import os
import io
from pathlib import Path

# Fix Windows terminal encoding for Unicode
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services import image_service, ocr_service, extraction_service
from app.compliance.scoring import calculate_score, get_grade_description
from app.services.report_service import ReportGenerator
from app.core.config import get_settings


def process_image(image_path: Path) -> dict:
    """Process a single image through OCR and extraction."""
    print(f"\n{'='*60}")
    print(f"Processing: {image_path.name}")
    print(f"{'='*60}")
    
    # Read image
    with open(image_path, "rb") as f:
        data = f.read()
    
    # Preprocess
    print("  Preprocessing image...")
    preprocessed = image_service.preprocess(data)
    print(f"    Steps applied: {preprocessed.steps_applied}")
    
    # OCR
    print("  Running OCR...")
    ocr_result = ocr_service.run_ocr(preprocessed.grayscale, preprocessed.steps_applied)
    print(f"    OCR confidence: {ocr_result.confidence_score:.2%}")
    print(f"    Text blocks found: {len(ocr_result.blocks)}")
    
    # Show raw text preview
    raw_text = ocr_result.lenient_text or ocr_result.raw_text
    if raw_text:
        preview = raw_text[:200].replace('\n', ' ')
        print(f"    Text preview: {preview}...")
    
    # Extraction
    print("  Extracting fields...")
    extraction = extraction_service.run_extraction(raw_text)
    print(f"    Fields extracted: {len(extraction.fields)}")
    
    # Show extracted fields
    for name, field in extraction.fields.items():
        print(f"      - {name}: {field.value}")
    
    return {
        "raw_text": raw_text,
        "extraction": extraction,
        "ocr_confidence": ocr_result.confidence_score,
    }


def generate_report(image_name: str, ocr_data: dict, output_dir: Path) -> Path:
    """Generate PDF report for the processed image."""
    print(f"\n  Generating PDF report...")
    
    # Calculate compliance score
    extraction = ocr_data["extraction"]
    compliance_score = calculate_score(extraction)
    
    print(f"\n  Compliance Score: {compliance_score.total_score:.1f}/100")
    print(f"  Grade: {compliance_score.grade} - {get_grade_description(compliance_score.grade)}")
    print(f"\n  Parameter Breakdown:")
    for param in compliance_score.parameters:
        status = "PASS" if param.present else "FAIL"
        print(f"    [{status}] {param.name} ({param.priority}): {param.points:.1f}/{param.weight * 100:.1f}")
    
    # Build analysis data
    analysis_data = {
        "analysis_id": f"test_{image_name.replace(' ', '_').replace('.', '_')}",
        "product": {
            "name": extraction.get("commodity_name").value if extraction.has("commodity_name") else "Unknown Product",
            "category": "Packaged Commodity",
            "subcategory": "Test Analysis",
            "classification_confidence": 0.9,
        },
        "overall_status": "COMPLETED",
        "summary": {
            "PASS": sum(1 for p in compliance_score.parameters if p.present),
            "FAIL": sum(1 for p in compliance_score.parameters if not p.present),
            "REVIEW": 0,
            "NOT_APPLICABLE": 0,
        },
        "compliance_score": compliance_score.get_summary(),
        "rules": [],  # Add rules if needed
    }
    
    # Generate PDF
    settings = get_settings()
    settings.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    generator = ReportGenerator()
    report_path = generator.generate(analysis_data, compliance_score)
    
    print(f"\n  PDF generated: {report_path}")
    return report_path


def main():
    """Main test function."""
    print("=" * 60)
    print("PRODUCT IMAGE COMPLIANCE TEST")
    print("=" * 60)
    
    # Find images in productimage folder
    product_image_dir = project_root / "productimage"
    
    if not product_image_dir.exists():
        print(f"Error: Directory not found: {product_image_dir}")
        print("Creating test directory...")
        product_image_dir.mkdir(exist_ok=True)
        print(f"Please add product images to: {product_image_dir}")
        return
    
    # Get all image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
    images = [
        f for f in product_image_dir.iterdir()
        if f.suffix.lower() in image_extensions
    ]
    
    if not images:
        print(f"\nNo images found in {product_image_dir}")
        print("Supported formats: JPG, JPEG, PNG, BMP, TIFF")
        return
    
    print(f"\nFound {len(images)} images to process")
    
    # Process each image
    results = []
    for i, image_path in enumerate(images, 1):
        print(f"\n[{i}/{len(images)}] Processing {image_path.name}...")
        
        try:
            # Process image
            ocr_data = process_image(image_path)
            
            # Generate report
            report_path = generate_report(image_path.name, ocr_data, product_image_dir / "reports")
            
            results.append({
                "image": image_path.name,
                "report": report_path,
                "success": True,
            })
            
        except Exception as e:
            print(f"\n  ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append({
                "image": image_path.name,
                "error": str(e),
                "success": False,
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total images processed: {len(results)}")
    print(f"Successful: {sum(1 for r in results if r['success'])}")
    print(f"Failed: {sum(1 for r in results if not r['success'])}")
    
    print("\nGenerated Reports:")
    for r in results:
        if r['success']:
            print(f"  [OK] {r['image']}")
            print(f"    Report: {r['report']}")
        else:
            print(f"  [FAIL] {r['image']}: {r['error']}")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
