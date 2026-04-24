# ... (imports and parser remain the same)

if st.button("🚀 Start Deep Scan & Map"):
    try:
        files_found = []
        # ... (path formatting logic)
        with st.spinner("Mapping Library..."):
            res = dbx.files_list_folder(formatted_path, recursive=True)
            
            def process_entries(entries):
                for entry in entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        if entry.name.lower().endswith(('.mp3', '.m4a', '.wav')):
                            artist, title = parse_music_filename(entry.name)
                            # KAIZEN: Use parent folder as Album
                            raw_folder = os.path.basename(os.path.dirname(entry.path_display))
                            folder_name = raw_folder if raw_folder else "Root"
                            
                            files_found.append({
                                "Name": title,
                                "Artist": artist,
                                "Album": folder_name, # Folder becomes Album for Triple-Match
                                "Source": "Cloud Library", # New dedicated column
                                "Full Path": entry.path_display
                            })
            # ... (pagination and loop)

            if files_found:
                df = pd.DataFrame(files_found)
                st.session_state['cloud_inventory'] = df
                st.success(f"Mapping Complete: {len(df)} tracks indexed.")

# ... (Search and Export)
    # GREELEY KAIZEN: Include the new Source column in the export
    master_csv = df[['Name', 'Artist', 'Album', 'Source', 'Full Path']].to_csv(index=False).encode('utf-8')
