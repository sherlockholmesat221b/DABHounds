# 🐾 DABHounds

**DABHounds** is a command-line utility that converts Spotify and YouTube playlists or individual tracks into [DABMusic](https://dabmusic.xyz) libraries by matching tracks and generating compatible playlists.  
It supports multiple matching modes to optimize accuracy and lets you authenticate with both DAB and Spotify for private content access.

---

## 🚀 Features

- Input from Spotify, YouTube, or ISRC codes  
- Three matching modes:  
  - **strict** — match only by ISRC  
  - **lenient** — fallback to fuzzy matching if ISRC unavailable  
  - **manual** — interactive track selection from search results  
- Login and logout management for DAB and Spotify  
- Customizable fuzzy matching threshold  
- Shows credits and version info  
- Update check feature

---

## 📥 Installation

### Install via PyPI:

```bash
pip install dabhounds
```

---

## 💡 Usage

Once installed, the dabhounds command is available globally:

### Show Version

```bash
dabhounds --version
```


### Show Help
```bash
dabhounds --help
```


### Convert a Spotify or YouTube Link

```bash
dabhounds <spotify_or_youtube_link>
```


### Select Matching Mode

```bash
dabhounds <link> --mode lenient
```


### Authenticate with DAB

```bash
dabhounds --login
```


### Authenticate with Spotify (OAuth)
```bash
dabhounds --spotify-login
```
**Note**: To setup Spotify OAuth, refer to this [guide](https://rentry.co/dabhounds-spotify-setup)


### Logout

```bash
dabhounds --logout
```


### Adjust Fuzzy Match Threshold

```bash
dabhounds <link> --threshold 85
```


### Display Credits

```bash
dabhounds --credits
```


### Check for Updates

```bash
dabhounds --update
```


---

## ⚙️ Command-Line Options

| Option                        | Description                                    |
|-------------------------------|-----------------------------------------------|
| `<link>`                       | Spotify, YouTube URL, or ISRC input           |
| `--mode {strict,lenient,manual}` | Choose matching mode (default: lenient)       |
| `--login`                       | Log in to DAB (required for library creation) |
| `--logout`                      | Log out from DAB and Spotify                  |
| `--spotify-login`               | Authenticate with Spotify via OAuth (optional)|
| `--threshold <0-100>`           | Set fuzzy search match threshold percentage  |
| `--version`                     | Show current version                           |
| `--credits`                     | Show tool credits and acknowledgements       |
| `--update`                      | Check for updates                              |


---

## 🧩 Dependencies

- Python 3.7 or higher
- Installed automatically via pip:
  - requests
  - spotipy
  - yt-dlp
  - musicbrainzngs
  - rapidfuzz


---

## 🌐 About DABMusic

[DABMusic](https://dabmusic.xyz) is a community-driven, digital music streaming platform focused on high-quality, unrestricted music access.


---

## 👥 Credits

- **Developer:** [sherlockholmesat221b](https://github.com/sherlockholmesat221b) (sherlockholmesat221b@proton.me)
- **superadmin0 (Creator of DABMusic)** — for building and maintaining DABMusic, the rock-solid foundation for this tool.
- [**uimaxbai (Contributor/Developer at DABMusic)**](https://github.com/uimaxbai) — for guiding the development of this tool and testing it firsthand.
- [**joehacks (Contributor/Developer at DABMusic)**](https://github.com/holmesisback) — for testing the tool firsthand.
- [**Squid.WTF**](https://squid.wtf) — for graciously allowing the use of their API.

---

## 📝 License

### GNU Affero General Public License v3.0.0.
Copyright (C) 2025 [sherlockholmesat221b](mailto:sherlockholmesat221b@proton.me)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty o 
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.
  
You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
