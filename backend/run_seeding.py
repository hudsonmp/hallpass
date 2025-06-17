#!/usr/bin/env python3
"""
Simple script to run user seeding for the SchoolSecure system.
This script calls the existing seed_users.py and provides clear feedback.
"""

import subprocess
import sys
import os

def run_seeding():
    """
    Run the user seeding script and provide clear feedback.
    """
    print("🚀 Starting SchoolSecure User Seeding Process...")
    print("=" * 60)
    
    # Change to the backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)
    
    try:
        # Run the seed script
        result = subprocess.run([sys.executable, "seed_users.py"], 
                              capture_output=True, text=True, check=True)
        
        print("✅ User seeding completed successfully!")
        print("\nOutput:")
        print(result.stdout)
        
        if result.stderr:
            print("\nWarnings/Info:")
            print(result.stderr)
            
        print("\n" + "=" * 60)
        print("🎉 Your test users are ready!")
        print("\n📧 You can now log in with any of these accounts:")
        print("   • hudsonmitchellpullman+admin@gmail.com (Administrator)")
        print("   • hudsonmitchellpullman+teacher1@gmail.com (Teacher)")
        print("   • hudsonmitchellpullman+student1@gmail.com (Student)")
        print("   • Password for all accounts: 2010Testing!")
        print("\n🔗 API Documentation available at: http://127.0.0.1:8000/docs")
        
    except subprocess.CalledProcessError as e:
        print("❌ User seeding failed!")
        print(f"Error: {e}")
        if e.stdout:
            print("\nOutput:")
            print(e.stdout)
        if e.stderr:
            print("\nError details:")
            print(e.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_seeding() 