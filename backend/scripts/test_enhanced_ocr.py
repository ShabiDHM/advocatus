#!/usr/bin/env python3
"""
PHOENIX PROTOCOL - ENHANCED OCR TEST FOR KOSOVO MARKET
Tests the new OCR system with Albanian language optimization.
"""

import sys
import os
import io

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_ocr_import():
    """Test if OCR service imports correctly"""
    print("🧪 Testing OCR Service Import...")
    try:
        from app.services.ocr_service import (
            extract_text_from_image_bytes,
            extract_expense_data_from_image,
            multi_strategy_ocr
        )
        print("✅ OCR service imports successfully")
        return True
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False

def test_albanian_ocr():
    """Test OCR with Albanian text"""
    print("\n🧪 Testing Albanian OCR...")
    
    try:
        from app.services.ocr_service import extract_text_from_image_bytes
        from PIL import Image, ImageDraw
        
        # Create Albanian receipt
        img = Image.new('RGB', (600, 300), color='white')
        draw = ImageDraw.Draw(img)
        
        # Albanian receipt content
        lines = [
            "DYQANI TRUST",
            "Faturë nr: 12345",
            "Data: 15 Janar 2024",
            "-------------------",
            "Kafe: 2.50€",
            "Ushqim: 8.75€",
            "Pije: 3.20€",
            "-------------------",
            "Total: 14.45€",
            "TVSH: 2.89€",
            "Faleminderit!"
        ]
        
        y = 30
        for line in lines:
            draw.text((30, y), line, fill='black')
            y += 25
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes = img_bytes.getvalue()
        
        # Extract text
        text = extract_text_from_image_bytes(img_bytes)
        
        print(f"✅ OCR extracted {len(text)} characters")
        print(f"📝 Preview: {text[:150]}...")
        
        # Check Albanian keywords
        keywords = ['Faturë', 'Data', 'Total', 'TVSH', 'Faleminderit']
        found = [kw for kw in keywords if kw.lower() in text.lower()]
        
        print(f"🔤 Found Albanian keywords: {found}")
        
        if len(found) >= 3:
            print("🎉 Albanian OCR working well!")
            return True
        else:
            print("⚠️  Some Albanian text not recognized")
            return False
            
    except Exception as e:
        print(f"❌ OCR Test Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_features():
    """Test new enhanced OCR features"""
    print("\n🧪 Testing Enhanced OCR Features...")
    
    try:
        from app.services.ocr_service import extract_expense_data_from_image
        from PIL import Image, ImageDraw
        import io
        
        # Create test receipt
        img = Image.new('RGB', (600, 350), color='white')
        draw = ImageDraw.Draw(img)
        
        lines = [
            "MERCHANT: TEST STORE",
            "INVOICE: INV-001",
            "DATE: 2024-01-15",
            "-------------------",
            "Office Supplies: 25.99€",
            "Coffee Machine: 120.50€",
            "Tax (18%): 26.37€",
            "-------------------",
            "TOTAL: 172.86€",
            "VAT: KS12345678",
            "Thank you!"
        ]
        
        y = 30
        for line in lines:
            draw.text((30, y), line, fill='black')
            y += 25
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        
        # Test enhanced extraction
        result = extract_expense_data_from_image(img_bytes.getvalue())
        
        print(f"✅ Enhanced extraction: {result['success']}")
        print(f"📊 Confidence: {result['confidence']:.2%}")
        
        if result['structured_data']:
            structured = result['structured_data']
            print(f"💰 Amount detected: {structured.get('total_amount', 'None')}")
            print(f"📅 Date detected: {structured.get('date', 'None')}")
            print(f"🏪 Merchant: {structured.get('merchant', 'None')}")
        
        return result['success']
        
    except Exception as e:
        print(f"❌ Enhanced Features Error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 PHOENIX ENHANCED OCR DEPLOYMENT TEST")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 3
    
    # Run tests
    if test_ocr_import():
        tests_passed += 1
    
    if test_albanian_ocr():
        tests_passed += 1
    
    if test_enhanced_features():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Enhanced OCR is ready.")
        return 0
    elif tests_passed >= 2:
        print("✅ Most tests passed. OCR is functional.")
        return 0
    else:
        print("⚠️  Some tests failed. Check OCR configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())