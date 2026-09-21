# Terminal recordings

Self-hosted asciicast v2 recordings from the Crucible synthetic batch demo.
Player: asciinema-player 3.17.0, vendored with its Apache-2.0 license in vendor/.
Source recordings: Crucible/demos/ignition-terminal; published copies come from
Crucible/crucible-website/assets/demos/. No live gateway or external host is required.

To update, replace the matching .cast after reviewing its output and checking
for credentials. Keep index.html/player.js and the vendor assets together.
Playback is user-initiated and pauses when offscreen or the document is hidden.

## README animations

The GIFs are rendered from the same casts for inline GitHub README playback.
Regenerate with agg 1.9.0 and the Menlo font, from this directory:

```sh
agg --font-family Menlo --font-size 14 --fps-cap 10 --speed 1.2 --idle-time-limit 2 --last-frame-duration 3 pi.cast pi.gif

```

README images link to the documentation player for pause, seeking, and fullscreen.
