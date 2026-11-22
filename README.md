# Garden Restaurant · IRL Garden Gaiden

`docs/` contains the new, build-free homepage. `snapshot/` contains the public WordPress export and its crawl manifest. Keep both in Git if you want the reference archive, and publish only `docs/`.

## Run and publish

Run `python -m http.server 8768 --directory docs` from the repository root, then open `http://localhost:8768`. For GitHub Pages, select the repository branch and its `/docs` directory as the publishing source. All site assets use relative paths.

## WeOrder

Garden's existing WeOrder URL is configured in `docs/weorder-config.js`. The live menu rendered in the iframe below the hero in a browser. WeOrder owns the menu, prices, basket and checkout. Verify payments on the final domain with the restaurant's test process before launch.

The host page cannot read the inside of the WeOrder frame. The sound toggle plays the original chime as a preview. Order-triggered sound requires a provider-documented order-completion message from the embedded storefront. `completionType` is disabled by default. It can be enabled for a documented `postMessage` with `{type, orderId}`; the handler verifies the iframe source, exact origin and unique order ID. Adapt the handler if WeOrder supplies a different official contract.

## Hero media

The current silent loop uses the restaurant's published stills, including the two chefs presented on its team page. The main title and controls live in HTML. The separate CapCut edit pack is for the planned production footage. Export the finished opening as H.264 MP4 with a 16:9 frame and save it to `docs/assets/garden-opening.mp4`. Replace `hero-poster.jpg` with an appropriate frame. The site respects reduced-motion preferences and provides a pause control.

To regenerate the current film, original pixel sprites, and order chime, install Pillow and run `python tools/make-media.py --ffmpeg /path/to/ffmpeg`.

## Snapshot scope

Read `snapshot/crawl-manifest.json` for the captured URLs and exact failures. The export preserves reachable HTML, styling, scripts, and downloaded media. The WordPress database, admin area, commerce sessions, and private plugin source require an authorized server export. The recoverable snapshot disables legacy POST forms, strips known nonce fields, and replaces the Google Maps API-key embed with a keyless one. Public themes and media retain their original ownership and licensing.

To refresh the snapshot, install lxml and run `python tools/crawl.py snapshot --cache ../garden-crawl-cache`. The crawler respects HTTP rate limits. Leave its local cache out of Git.
