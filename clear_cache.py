import os
import shutil

# Hapus semua cache
folders = ['__pycache__', 'static/.cache', 'templates/.cache']
for folder in folders:
    if os.path.exists(folder):
        shutil.rmtree(folder)
        print(f"Deleted: {folder}")

# Hapus browser cache simulation
print("\nSekarang di browser:")
print("1. F12 → Network → Centang 'Disable cache'")
print("2. Ctrl+Shift+R (Hard Refresh)")
print("3. Atau buka incognito window")