"""
Test compliance for ALL response templates (diversion, short, cool)
Run: docker-compose exec backend python test_all_template_compliance.py
"""
import re
import os
import sys

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flirty_backend.settings')

import django
django.setup()

from accounts.services.response_validator import ResponseValidator
from django.contrib.auth.models import User

# Get test user
test_user, _ = User.objects.get_or_create(
    username='blog_compliance_test',
    defaults={'email': 'test@blog.com'}
)

# Create validator to get diversion templates
validator = ResponseValidator(test_user)
DIVERSION_TEMPLATES = validator.diversion_templates

# Dynamically extract SHORT and COOL templates from ai_generation.py file
# by reading the file and parsing them
import re as regex_module

def extract_templates_from_file(filepath, template_name):
    """Extract template list from Python file"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find the template list
    pattern = rf'{template_name}\s*=\s*\[(.*?)\]'
    match = regex_module.search(pattern, content, regex_module.DOTALL)
    if match:
        list_content = match.group(1)
        # Extract strings
        strings = regex_module.findall(r'"([^"]*)"', list_content)
        return strings
    return []

backend_path = '/app/accounts/services/ai_generation.py'
SHORT_TEMPLATES = extract_templates_from_file(backend_path, 'short_templates')
COOL_TEMPLATES = extract_templates_from_file(backend_path, 'cool_templates')

BANNED_WORDS = [
    r'\bguessing\b', r'\bmysterious\b', r'\bplayful\b', r'\btempting\b', r'\bintriguing\b',
    r'\bwhat would you do if\b', r'\bwhat about you\b', r'\bI want to keep you\b',
    r'\bcertainly\b', r'\babsolutely\b', r'\bof course\b', r'\bgreat question\b',
    r'\bdelve\b', r'\bleverage\b', r'\butilize\b', r'\bfurthermore\b', r'\bmoreover\b'
]

def test_compliance(response):
    """Test single response for all compliance rules"""
    issues = []
    
    # Check banned words
    for pattern in BANNED_WORDS:
        if regex_module.search(pattern, response, regex_module.IGNORECASE):
            issues.append(f"Banned word: {pattern}")
    
    # Check starts with "I"
    if response.strip().lower().startswith('i '):
        issues.append("Starts with 'I'")
    
    # Check length
    if not (140 <= len(response) <= 180):
        issues.append(f"Length {len(response)} not in 140-180 range")
    
    # Check ends with ?
    if not response.rstrip().endswith('?'):
        issues.append("Doesn't end with ?")
    
    # Check has contractions
    if not regex_module.search(r"(don't|can't|won't|I'm|you're|it's|that's|there's|what's|doesn't|i'm|you're)", response, regex_module.IGNORECASE):
        issues.append("May be missing contractions")
    
    return issues

# Test all templates
print("\n" + "="*80)
print("COMPREHENSIVE BLOG COMPLIANCE TEST - ALL TEMPLATES")
print("="*80)

all_violations = 0
test_count = 0

# Test diversion templates
print("\n" + "="*40)
print(f"DIVERSION TEMPLATES ({len(DIVERSION_TEMPLATES)} total)")
print("="*40)
for idx, tmpl in enumerate(DIVERSION_TEMPLATES, 1):
    test_count += 1
    issues = test_compliance(tmpl)
    print(f"\n{idx}. ({len(tmpl)} chars) {tmpl[:50]}...")
    if issues:
        print(f"   ❌ Issues: {', '.join(issues)}")
        all_violations += 1
    else:
        print(f"   ✅ PASS")

# Test short templates
print("\n" + "="*40)
print(f"SHORT TEMPLATES ({len(SHORT_TEMPLATES)} total)")
print("="*40)
for idx, tmpl in enumerate(SHORT_TEMPLATES, 1):
    test_count += 1
    issues = test_compliance(tmpl)
    print(f"\n{idx}. ({len(tmpl)} chars) {tmpl[:50]}...")
    if issues:
        print(f"   ❌ Issues: {', '.join(issues)}")
        all_violations += 1
    else:
        print(f"   ✅ PASS")

# Test cool templates
print("\n" + "="*40)
print(f"COOL TEMPLATES ({len(COOL_TEMPLATES)} total)")
print("="*40)
for idx, tmpl in enumerate(COOL_TEMPLATES, 1):
    test_count += 1
    issues = test_compliance(tmpl)
    print(f"\n{idx}. ({len(tmpl)} chars) {tmpl[:50]}...")
    if issues:
        print(f"   ❌ Issues: {', '.join(issues)}")
        all_violations += 1
    else:
        print(f"   ✅ PASS")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total templates tested: {test_count}")
print(f"Diversion: {len(DIVERSION_TEMPLATES)} | Short: {len(SHORT_TEMPLATES)} | Cool: {len(COOL_TEMPLATES)}")
print(f"Templates with violations: {all_violations}")
print(f"Templates passing compliance: {test_count - all_violations}")

if all_violations == 0:
    print("\n✅ ALL TEMPLATES PASS BLOG COMPLIANCE!")
else:
    print(f"\n❌ {all_violations} templates have violations")

print("\nCompleted at:", os.popen('date').read().strip())

