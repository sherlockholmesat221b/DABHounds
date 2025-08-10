# 🐾 DABHounds

**DABHounds** is a command-line utility that converts Spotify and YouTube playlists or individual tracks into [DABMusic](https://dab.yeet.su) libraries by matching tracks and generating compatible playlists.  
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
- Update check feature (currently not implemented)  

---

## 📥 Installation

Clone and install dependencies:

```bash
git clone https://github.com/sherlockholmesat221b/dabhounds.git
cd dabhounds
pip install -r requirements.txt
````

Run the tool using Python 3.7+:

```bash
python dabhounds.py <link> [--mode strict|lenient|manual]
```

---

## 💡 Usage

### Basic Conversion

Convert a Spotify or YouTube link to a DAB library:

```bash
python dabhounds.py <spotify_or_youtube_link>
```

### Select Matching Mode

Specify the matching mode (`strict`, `lenient`, or `manual`):

```bash
python dabhounds.py <link> --mode lenient
```

### Authenticate with DAB

Login to your DAB account for access to protected libraries and to enable library creation:

```bash
python dabhounds.py --login
```

### Authenticate with Spotify (OAuth)

Login to Spotify for access to private playlists. Spotify login is optional and only required for private playlists. Other Spotify or YouTube inputs do not require Spotify login:

```bash
python dabhounds.py --spotify-login
```

### Logout

Logout from both DAB and Spotify accounts:

```bash
python dabhounds.py --logout
```

### Adjust Fuzzy Match Threshold

Override the default fuzzy search threshold (0-100):

```bash
python dabhounds.py <link> --threshold 85
```

### Display Credits and Version

Show acknowledgements or version information:

```bash
python dabhounds.py --credits
python dabhounds.py --version
```

### Check for Updates

Check if a new version is available:

```bash
python dabhounds.py --update
```

---

## ⚙️ Command-Line Options

| Option                           | Description                                    |
| -------------------------------- | ---------------------------------------------- |
| `<link>`                         | Spotify, YouTube URL, or ISRC input            |
| `--mode {strict,lenient,manual}` | Choose matching mode (default: lenient)        |
| `--login`                        | Log in to DAB (required for library creation)  |
| `--logout`                       | Log out from DAB and Spotify                   |
| `--spotify-login`                | Authenticate with Spotify via OAuth (optional) |
| `--threshold <0-100>`            | Set fuzzy search match threshold percentage    |
| `--version`                      | Show current version                           |
| `--credits`                      | Show tool credits and acknowledgements         |
| `--update`                       | Check for updates                              |

---

## 🧩 Dependencies

- Python 3.7 or higher
- Required Python packages (install via `requirements.txt`):
    - `requests
    - `spotipy`
    - `yt-dlp`
    - `musicbrainzngs`
    - `rapidfuzz`

---

## 🌐 About DABMusic

[DABMusic](https://dab.yeet.su) is a community-driven, open-source digital music library and streaming platform focused on high-quality, unrestricted music access.

---

## 👥 Credits

- **Developer:** [sherlockholmesat221b](https://github.com/sherlockholmesat221b) (sherlockholmesat221b@proton.me)
- **superadmin0 (Creator of DABMusic)** — for building and maintaining DABMusic, the rock-solid foundation for this tool.
- [**uimaxbai (Contributor/Developer at DABMusic)**](https://github.com/uimaxbai) — for guiding the development of this tool and testing it firsthand.
- [**joehacks (Contributor/Developer at DABMusic)**](https://github.com/holmesisback) — for testing the tool firsthand.
- [**Squid.WTF**](https:// squid.wtf) — for graciously allowing the use of their API.

---

## 📝 License

## MIT License

Copyright (c) 2025 sherlockholmesat221b

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
