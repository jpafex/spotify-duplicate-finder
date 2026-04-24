# ... (imports and config remains the same)

def parse_music_filename(filename):
    """
    HEAVY-DUTY PARSER: 
    1. Protects hyphenated names like K-Paz.
    2. Fallback logic for filenames with NO spaces (e.g., Artist-Title).
    """
    clean_name = os.path.splitext(filename)[0]
    # Remove noise
    noise = [r'\(.*?\)', r'\[.*?\]', r'feat\..*', r'ft\..*', r'\d{3}k', r'kbps', r'explicit']
    for p in noise:
        clean_name = re.sub(p, '', clean_name, flags=re.IGNORECASE)
    
    clean_name = clean_name.strip(' .-_')
    
    # Try the 'Space-Dash-Space' first (Precision Mode)
    precision_pattern = r"^(?:\d+\s*[.\-_]?\s*)?(.+?)\s+[\-_–—]\s+(.+)$"
    match = re.match(precision_pattern, clean_name)
    
    if match:
        return match.group(1).strip(), match.group(2).strip()
    
    # Fallback: If no space-dash-space, try any dash (Standard Mode)
    standard_pattern = r"^(?:\d+\s*[.\-_]?\s*)?(.+?)[\-_–—](.+)$"
    match = re.match(standard_pattern, clean_name)
    if match:
        return match.group(1).strip(), match.group(2).strip()
        
    return "Unknown Artist", clean_name.strip()

# ... (connection and scan logic remains the same)

# GREELEY KAIZEN: Use standard 'utf-8' to avoid the BOM issue in the Gap Mirror
if 'cloud_inventory' in st.session_state:
    df = st.session_state['cloud_inventory']
    # ... (search and display logic)
    master_csv = df[['Name', 'Artist', 'Album', 'Folder', 'Full Path']].to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Corrected Master Inventory",
        data=master_csv,
        file_name=f"Dropbox_Fixed_Inventory_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
