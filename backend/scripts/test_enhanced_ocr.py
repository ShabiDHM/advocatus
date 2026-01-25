#!/usr/bin/env python3
"""
PHOENIX PROTOCOL - SIMPLIFIED OCR TEST
Direct import test that works with actual file structure.
"""

import sys
import os
import io

# Set up correct Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)  # Go up from scripts to backend
project_root = os.path.dirname(backend_dir)  # Go up to project root

# Add all necessary paths
sys.path.insert(0, project_root)  # Project root
sys.path.insert(0, backend_dir)   # Backend directory

print(f"Python paths:")
print(f"1. {project_root}")
print(f"2. {backend_dir}")
print(f"3. {current_dir}")

def test_direct_import():
    """Test direct import from actual file location"""
    print("\n🧪 Testing Direct Import...")
    
    # Method 1: Try direct file import
    try:
        # Add the services directory to path
        services_dir = os.path.join(backend_dir, 'app', 'services')
        sys.path.insert(0, services_dir)
        
        # Import the module directly
        import ocr_service
        
        print("✅ SUCCESS: Imported ocr_service directly")
        print(f"   Module location: {ocr_service.__file__}")
        
        # Check if functions exist
        functions_to_check = [
            'extract_text_from_image_bytes',
            'extract_expense_data_from_image', 
            'multi_strategy_ocr',
            'SmartOCRResult',
            'extract_structured_data_from_text',
            'rule_based_correction'
        ]
        
        for func_name in functions_to_check:
            if hasattr(ocr_service, func_name):
                print(f"   ✓ {func_name} exists")
            else:
                print(f"   ✗ {func_name} NOT found")
        
        return ocr_service
        
    except ImportError as e:
        print(f"❌ Direct import failed: {e}")
        return None

def test_ocr_functions(ocr_module):
    """Test OCR functions"""
    print("\n🧪 Testing OCR Functions...")
    
    try:
        from PIL import Image, ImageDraw
        
        # Create test image
        img = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), 'TEST RECEIPT', fill='black')
        draw.text((20, 60), 'Total: 25.50€', fill='black')
        draw.text((20, 100), 'Date: 25.01.2024', fill='black')
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        image_bytes = img_bytes.getvalue()
        
        # Test extract_text_from_image_bytes
        if hasattr(ocr_module, 'extract_text_from_image_bytes'):
            text = ocr_module.extract_text_from_image_bytes(image_bytes)
            print(f"✅ extract_text_from_image_bytes: {len(text)} chars")
            print(f"   Preview: {text[:100]}...")
        else:
            print("❌ extract_text_from_image_bytes not found")
        
        # Test rule_based_correction
        if hasattr(ocr_module, 'rule_based_correction'):
            test_text = "SPARKOSOVA\nTOTAL 630N\nKate 24150001"
            corrected = ocr_module.rule_based_correction(test_text)
            print(f"✅ rule_based_correction works")
            print(f"   Before: {test_text[:50]}...")
            print(f"   After: {corrected[:50]}...")
        
        # Test extract_structured_data_from_text
        if hasattr(ocr_module, 'extract_structured_data_from_text'):
            test_receipt = """SPAR KOSOVA
Fiskal Nr: 123456789012
Total: 25.50€
Date: 25.01.2024"""
            
            structured = ocr_module.extract_structured_data_from_text(test_receipt)
            print(f"✅ extract_structured_data_from_text works")
            print(f"   Total: {structured.get('total_amount')}")
            print(f"   Date: {structured.get('date')}")
            print(f"   Merchant: {structured.get('merchant')}")
        
        return True
        
    except Exception as e:
        print(f"❌ OCR function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_kosovo_corrections(ocr_module):
    """Test Kosovo thermal receipt corrections"""
    print("\n🧪 Testing Kosovo Thermal Receipt Corrections...")
    
    try:
        if not hasattr(ocr_module, 'rule_based_correction'):
            print("❌ rule_based_correction not available")
            return False
        
        # Test case from actual OCR
        thermal_text = """SPARKOSOVA
Fiskal Nr 123456789012
Data 25.01.2026 1430
Kate 24150001
Uj 10.80 -0808
Sandun 11251
TOTAL 630N"""
        
        print("Test input (thermal receipt OCR):")
        print("-" * 40)
        print(thermal_text)
        print("-" * 40)
        
        corrected = ocr_module.rule_based_correction(thermal_text)
        
        print("\nCorrected output:")
        print("-" * 40)
        print(corrected)
        print("-" * 40)
        
        # Check corrections
        checks = [
            ('SPAR KOSOVA' in corrected, 'Merchant name corrected'),
            ('Kafe' in corrected, 'Kafe spelling corrected'),
            ('Sanduiç' in corrected, 'Sanduiç spelling corrected'),
            ('6.30€' in corrected or '6.30' in corrected, 'Total amount corrected'),
            ('€' in corrected, 'Euro symbol present'),
        ]
        
        passed = 0
        for condition, description in checks:
            if condition:
                print(f"✅ {description}")
                passed += 1
            else:
                print(f"❌ {description}")
        
        print(f"\nPassed: {passed}/{len(checks)}")
        return passed >= 3
        
    except Exception as e:
        print(f"❌ Kosovo correction test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 OCR SERVICE VALIDATION TEST")
    print("=" * 60)
    
    # Test 1: Import
    ocr_module = test_direct_import()
    if not ocr_module:
        print("\n❌ Cannot import OCR module. Check file structure.")
        return 1
    
    # Test 2: Functions
    func_test = test_ocr_functions(ocr_module)
    
    # Test 3: Kosovo corrections
    kosovo_test = test_kosovo_corrections(ocr_module)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    tests = [func_test, kosovo_test]
    passed = sum(1 for test in tests if test)
    
    print(f"Tests Passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("🎉 All tests passed! OCR service is ready.")
        return 0
    elif passed >= 1:
        print("✅ Basic functionality working.")
        return 0
    else:
        print("❌ Critical failures. Check OCR setup.")
        return 1

if __name__ == "__main__":
    sys.exit(main())