import json
import os

FILE_PATH = "kjc_judicial_data.json"

def audit_data():
    print("🕵️  AUDITING KJC DATA COVERAGE...")
    
    if not os.path.exists(FILE_PATH):
        print("❌ Data file not found. Please run the fetch script first.")
        return

    with open(FILE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"📄 Total Records Fetched: {len(data)}")

    # 1. Group by Court
    courts = {}
    for item in data:
        court_name = item.get("CourtName", "Unknown")
        if court_name not in courts:
            courts[court_name] = []
        courts[court_name].append(item.get("JudgeFullName"))

    # 2. Print Report
    print("\n🗺️  COURT COVERAGE MAP:")
    print(f"   (Found {len(courts)} distinct courts/branches)\n")
    
    total_judges = 0
    for court, judges in courts.items():
        count = len(judges)
        total_judges += count
        # print first 3 judges as sample
        sample = ", ".join(judges[:3])
        print(f"   📍 {court}: {count} Judges/Entries")
        # print(f"      (e.g., {sample}...)")

    print(f"\n✅ Total Entries: {total_judges}")
    
    # 3. Check for Major Missing Cities
    major_cities = ["Prishtinë", "Prizren", "Pejë", "Mitrovicë", "Gjilan", "Ferizaj", "Gjakovë"]
    print("\n🔍 GAP ANALYSIS (Major Centers):")
    found_text = " ".join(courts.keys())
    
    for city in major_cities:
        if city in found_text or city[:-1] in found_text: # Handle suffix variations
            print(f"   ✅ {city}: PRESENT")
        else:
            print(f"   ❌ {city}: MISSING (Critical Gap)")

if __name__ == "__main__":
    audit_data()