import os
import zipfile
import time
from datetime import datetime

def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            if file != 'vehicle_booking.zip' and '.git' not in root:  # Skip the zip file itself
                try:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, path)
                    # Use current time for all files to avoid timestamp issues
                    zipinfo = zipfile.ZipInfo(arcname)
                    # Use current time (ZIP format doesn't accept dates before 1980)
                    current_time = time.localtime(time.time())[:6]
                    zipinfo.date_time = current_time
                    zipinfo.compress_type = zipfile.ZIP_DEFLATED
                    
                    # Read file data
                    with open(file_path, 'rb') as f:
                        data = f.read()
                    
                    # Write file to zip with controlled timestamp
                    ziph.writestr(zipinfo, data)
                except Exception as e:
                    print(f"Error adding {file_path}: {e}")

if __name__ == '__main__':
    zipf = zipfile.ZipFile('vehicle_booking.zip', 'w')
    zipdir('.', zipf)
    zipf.close()
    
    print("ZIP file created successfully: vehicle_booking.zip")
    print("You can now download this file from the file explorer.")
    print("Look for the file in the file list on the left side of your screen.")