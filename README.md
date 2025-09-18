This is the beta version of DABHounds, a TODO list is provided for reference. Feel free to use it as a guide and contribute improvements which shall be pushed to the main DABHounds.
# 2025-09-18
- [ ] Implement an improved downloader leveraging `tqdm`, modeled after the `dabcli` download pipeline.
    - Current Downloader Limitations:
        - [ ] Progress bar is minimal, lacking key details such as file size, download speed, and estimated time remaining.
        - [ ] Downloaded files do not include metadata (e.g., artist, album, track info) or cover art.
        - [ ] Filenames do not reflect track position, and no metadata is embedded. Support for `.m3u8` playlist generation (similar to `dabcli`) should be added.
        - [ ] The download directory is in the code repo, which will be inaccessible when pushed to pip. Change the download directory to $HOME (or whstever).
- [ ] Update `dabhounds/core/spotify_auth.py` to source Spotify credentials exclusively from `config.json`.

- [ ] Introduce synchronization logic:
    - When generating `report.txt`, record the original source URL (e.g., `https://youtube.com/?playlist=...`).
    - On execution, check `report.txt` for the recorded source URL.
    - If found, compare the referenced playlist with the DAB library to ensure consistency, automatically adding or removing tracks to maintain synchronization.
