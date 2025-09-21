# 🎶 Setting up Spotify OAuth for DABHounds

DABHounds can pull tracks from Spotify and convert them into DAB playlists. However, Spotify requires **OAuth client credentials** for anything that touches user data or editorial playlists, including private and collaborative playlists.  

Many developers initially try to ship a shared client ID/secret or use a test app. Spotify’s policies make this tricky: test apps are designed for **private use and limited users only**, and if they detect abuse or public distribution, the credentials can be revoked repeatedly. DABHounds experienced exactly this — apps in developer/test mode kept getting disabled.  

This guide explains how users can create their own Spotify app, add themselves as authorized testers, and avoid repeated bans while understanding the limits of public vs. private access.

---
## 🔓 What works without credentials?

- **Public tracks, albums, and playlists** that are globally visible often work with the client credentials flow.  
- Metadata for individual tracks or albums can be fetched without OAuth.  

This is enough for quick tests or basic conversions.  

---
## 🔒 What requires OAuth?

- **Private playlists**  
- **Collaborative playlists**  
- **Editorial playlists and mixes** curated by Spotify (e.g., mood mixes, “Made for You,” Discover Weekly)  
- Anything tied to your **personal account data**  

If you try to fetch these without OAuth, Spotify will usually return a **404 “Resource not found”**, even though the playlist exists.

---
## 🛠️ How to create your own Spotify app

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/) and log in with your Spotify account.  

2. Click **“Create an App.”**  
   - Give it a name like `DABHounds` or `My Playlist Converter`.  
   - Enter a simple description (e.g., “Personal use tool for playlist conversion”).  

3. Set a **Redirect URI** for OAuth authentication:  ```http://127.0.0.1:8888/callback```.
4. Save changes.
5. Copy your **Client ID** and **Client Secret**.  

---
## ⚠️ Test Mode Limitations

Spotify apps are initially in **developer/test mode**:  

- They can only be used by users you explicitly add as **testers**.  
- The app cannot be publicly distributed or published without going through Spotify’s review process.  
- To add a tester:  
1. Open your app in the Spotify Developer Dashboard.  
2. Click **“User Management”**.  
3. Enter a Name (Biggus Dickus) and email of the user (yourself) who need access.
4. Click on "Add User".

---
## ⚙️ Adding credentials to DABHounds

4. After finishing all of this, you can run DABHounds’ interactive login command, an example run is given below:

```bash
dabhounds --spotify-login
[DABHound] Spotify credentials not found in config.json.
[DABHound] See setup guide: https://example.com/dabhounds-spotify-setup
Enter your Spotify app credentials (from https://developer.spotify.com/dashboard):
  SPOTIFY_CLIENT_ID: <your-client-id-here>
  SPOTIFY_CLIENT_SECRET: <your-client-secret-here>
  SPOTIFY_REDIRECT_URI [http://127.0.0.1:8888/callback]:<press Enter>
Go to the following URL: https://accounts.spotify.com/authorize?client_id=<your-client-id-here>&response_type=code&redirect_uri=http%3A%2F%2F127.0.0.1%3A8888%2Fcallback&scope=playlist-read-private+playlist-read-collaborative
Enter the URL you were redirected to: http://127.0.0.1:8888/callback?code=<authorization-code>
[DABHound] Spotify login successful as: <Your Name>
```
On the next run, DABHounds will prompt you to log in to Spotify once. Your access and refresh tokens will be stored locally, so you won’t need to repeat the login unless you log out or delete your config.  

---
## ❓ FAQ

**Q: Do I need a paid Spotify account?**  
No. Free accounts can generate OAuth tokens and fetch playlists.  

**Q: Will Spotify ban me for using this?**  
Not probable.

**Q: Why can’t DABHounds ship credentials?**  
Because test-mode apps are limited to a small set of testers. Publicly sharing credentials triggers Spotify to revoke them repeatedly, which is exactly what happened in prior DABHounds builds.  

---

## ✅ Summary

- **Without OAuth:** fetch basic track/album metadata and some public playlists.  
- **With OAuth (personal app in test mode):** access private playlists, collaborative playlists, and editorial mixes.  
- **Steps for setup:** create a Spotify app, add yourself as a tester, enter credentials after running `dabhounds --spotify-login`, then log in.  

Following these steps ensures stable access.