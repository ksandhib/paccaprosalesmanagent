import os
import urllib.request
import ssl

def download_file(url, filepath):
    print(f"Downloading {url} to {filepath}...")
    try:
        # Create unverified context to avoid SSL handshake verification errors in restrictive environments
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(url, context=context) as response, open(filepath, 'wb') as out_file:
            out_file.write(response.read())
        print("Success.")
    except Exception as e:
        print(f"Failed to download {url}: {str(e)}")
        # Raise exception to halt setup if key files are missing
        raise e

def main():
    lib_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "lib"))
    os.makedirs(lib_dir, exist_ok=True)

    assets = {
        "bootstrap.min.css": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
        "jquery.dataTables.min.css": "https://cdn.datatables.net/1.13.7/css/jquery.dataTables.min.css",
        "jquery.min.js": "https://code.jquery.com/jquery-3.7.1.min.js",
        "bootstrap.bundle.min.js": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js",
        "chart.umd.js": "https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.js",
        "jquery.dataTables.min.js": "https://cdn.datatables.net/1.13.7/js/jquery.dataTables.min.js"
    }

    print("--- Starting Asset Downloader for Offline Capability ---")
    for filename, url in assets.items():
        filepath = os.path.join(lib_dir, filename)
        if not os.path.exists(filepath):
            download_file(url, filepath)
        else:
            print(f"{filename} already exists. Skipping.")
    print("--- Asset Downloader Completed Successfully ---")

if __name__ == "__main__":
    main()
