import json
import os
import urllib.request
from urllib.parse import urlparse

def extract_name_from_url(url):
    """Extracts, cleans, and formats the channel name from the stream URL."""
    def clean_name(raw_name):
        # Remove the "_MOB" suffix first, then replace underscores with spaces
        name = raw_name.replace("_MOB", "").replace("_", " ")
        # Catch any lingering " MOB" at the end just in case
        if name.endswith(" MOB"):
            name = name[:-4]
        return name.strip()

    try:
        # Parse the path from the URL
        path = urlparse(url).path
        # Split by '/' and remove empty strings
        parts = [p for p in path.split('/') if p] 
        
        # Most Jio URLs structure is: /bpk-tv/Channel_Name_Here/WDVLive/index.mpd
        if 'WDVLive' in parts:
            idx = parts.index('WDVLive')
            if idx > 0:
                return clean_name(parts[idx - 1])
                
        # Fallback: look for 'bpk-tv' and grab the folder right after it
        if 'bpk-tv' in parts:
            idx = parts.index('bpk-tv')
            if idx + 1 < len(parts):
                return clean_name(parts[idx + 1])
                
        # Final fallback if those specific folders aren't found
        if len(parts) >= 2:
            return clean_name(parts[-2])
            
    except Exception:
        pass
        
    return "Unknown Channel"

def generate_m3u_from_url(jio_url, meta_file, output_file):
    print(f"Fetching stream data from {jio_url}...")
    try:
        req = urllib.request.Request(jio_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                print(f"Error fetching URL: HTTP Status {response.status}")
                return
            raw_data = response.read().decode('utf-8')
            jio_data = json.loads(raw_data)
    except Exception as e:
        print(f"Error fetching or parsing the URL data: {e}")
        return

    meta_data = []
    if not os.path.exists(meta_file):
        print(f"Warning: {meta_file} not found. Proceeding without metadata.")
    else:
        with open(meta_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                print(f"Warning: {meta_file} is empty on disk. Save your file in the editor!")
            else:
                try:
                    meta_data = json.loads(content)
                except json.JSONDecodeError:
                    print(f"Error parsing {meta_file}. Ensure it is valid JSON.")
            
    # Create a dictionary for quick metadata lookup by "tvg-id"
    meta_dict = {str(item.get("tvg-id")): item for item in meta_data}
    
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write("#EXTM3U\n")
        
        for channel_id, stream_info in jio_data.items():
            url = stream_info.get("url", "")
            
            # Skip if there's no stream URL
            if not url:
                continue
                
            meta_info = meta_dict.get(str(channel_id), {})
            
            # Check if it's an unknown channel (not in meta.txt)
            if not meta_info:
                # Extract and format the name from the URL
                name = extract_name_from_url(url)
                logo = ""
                group = "Unknown"
            else:
                # Known channel, but fallback to URL extraction if name is missing
                name = meta_info.get("channel-name")
                if not name:
                    name = extract_name_from_url(url)
                    
                logo = meta_info.get("tvg-logo", "")
                group = meta_info.get("group-title", "Unknown")
                
            # A. Format the standard EXTINF line with metadata
            extinf = f'#EXTINF:-1 tvg-id="{channel_id}" tvg-logo="{logo}" group-title="{group}",{name}\n'
            
            # B. Add DRM properties for player compatibility
            drm_props = (
                '#KODIPROP:inputstream=inputstream.adaptive\n'
                '#KODIPROP:inputstream.adaptive.manifest_type=mpd\n'
                '#KODIPROP:inputstream.adaptive.license_type=clearkey\n'
                f'#KODIPROP:inputstream.adaptive.license_key=https://temp.webplay.fun/jtv/key.php?id={channel_id}\n'
            )
            
            # C. Write the compiled data block to the file
            out.write(extinf)
            out.write(drm_props)
            out.write(url + "\n\n")
            
    print(f"Success! M3U playlist generated as '{output_file}'.")

if __name__ == "__main__":
    # Use absolute paths relative to the script directory
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    JIO_URL = "https://jo-json.vodep39240327.workers.dev/"
    META_FILENAME = os.path.join(BASE_DIR, "meta.txt")
    # Output file will also be in the same folder
    OUTPUT_FILENAME = os.path.join(BASE_DIR, "jiotv.m3u")
    
    generate_m3u_from_url(JIO_URL, META_FILENAME, OUTPUT_FILENAME)
