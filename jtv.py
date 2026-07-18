import re
import json
from datetime import datetime
import requests

def parse_m3u_to_json(m3u_url):
    """
    Parse M3U playlist from URL and convert to JSON format
    """
    # Fetch the M3U content
    response = requests.get(m3u_url)
    response.raise_for_status()
    content = response.text
    
    lines = content.strip().split('\n')
    
    result = []
    current_entry = {}
    
    for line in lines:
        line = line.strip()
        
        if line.startswith('#EXTINF'):
            # Extract channel name from EXTINF line
            # Format: #EXTINF:-1 tvg-id="143" tvg-logo="..." group-title="English",CNBC TV18 Prime
            match = re.search(r',([^,]+)$', line)
            if match:
                channel_name = match.group(1).strip()
                current_entry['name'] = channel_name
            
            # Extract tvg-id if available
            tvg_id_match = re.search(r'tvg-id="([^"]+)"', line)
            if tvg_id_match:
                current_entry['id'] = tvg_id_match.group(1)
            else:
                current_entry['id'] = ''
                
        elif line.startswith('#KODIPROP:inputstream.adaptive.license_key'):
            # Extract license key
            # Format: #KODIPROP:inputstream.adaptive.license_key=key_id:key
            match = re.search(r'license_key=([^:]+):([^:]+)', line)
            if match:
                current_entry['key_id'] = match.group(1)
                current_entry['key'] = match.group(2)
                
        elif line.startswith('http') or line.startswith('https'):
            # Extract stream URL and cookie
            if '|' in line:
                url_parts = line.split('|')
                stream_url = url_parts[0]
                cookie_part = url_parts[1] if len(url_parts) > 1 else ''
                
                # Extract cookie
                cookie_match = re.search(r'Cookie=([^|]+)', cookie_part)
                if cookie_match:
                    current_entry['cookie'] = cookie_match.group(1)
                    
                    # Extract expiry timestamp from cookie
                    exp_match = re.search(r'exp=(\d+)', current_entry['cookie'])
                    if exp_match:
                        exp_timestamp = int(exp_match.group(1))
                        # Convert to datetime
                        exp_datetime = datetime.fromtimestamp(exp_timestamp)
                        current_entry['cookie_expires'] = exp_datetime.strftime('%d/%m/%Y %I:%M:%S %p IST')
                else:
                    current_entry['cookie'] = ''
                    current_entry['cookie_expires'] = ''
            else:
                stream_url = line
                current_entry['cookie'] = ''
                current_entry['cookie_expires'] = ''
            
            current_entry['stream_url'] = stream_url
            
            # If we have a complete entry, add to result
            if current_entry and 'name' in current_entry and 'stream_url' in current_entry:
                # Ensure all fields exist
                entry = {
                    'id': current_entry.get('id', ''),
                    'name': current_entry.get('name', ''),
                    'stream_url': current_entry.get('stream_url', ''),
                    'cookie': current_entry.get('cookie', ''),
                    'cookie_expires': current_entry.get('cookie_expires', ''),
                    'key_id': current_entry.get('key_id', ''),
                    'key': current_entry.get('key', '')
                }
                result.append(entry)
                
            # Reset for next entry
            current_entry = {}
            
    return result

def save_to_json(data, output_file='jtv.json'):
    """
    Save the parsed data to a JSON file
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"JSON file saved as: {output_file}")
    print(f"Total channels parsed: {len(data)}")

def main():
    # M3U URL
    m3u_url = 'https://raw.githubusercontent.com/sixpg/zeyo/refs/heads/main/jtv.m3u'
    
    try:
        # Parse M3U to JSON
        channels = parse_m3u_to_json(m3u_url)
        
        # Display first few channels as preview
        print("Preview of first 3 channels:")
        for i, channel in enumerate(channels[:3], 1):
            print(f"{i}. {channel['name']} - {channel['stream_url']}")
            
        # Save to JSON file as jtv.json
        save_to_json(channels, 'jtv.json')
        
        # Also display the total count and file location
        print(f"\n✅ Successfully saved {len(channels)} channels to jtv.json")
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching M3U file: {e}")
    except Exception as e:
        print(f"Error parsing M3U file: {e}")

if __name__ == "__main__":
    main()
