# Nonpartisan Chrome Extension

Manifest V3 browser extension built with [WXT](https://wxt.dev/) and React 19, allowing users to analyze diverse perspectives on the news story they are currently reading.

---

## Features

- **One-Click Perspective Analysis**: Extracts the headline and context from the active browser tab (with custom parsers and generic OpenGraph metadata extraction fallbacks) and submits it to the backend.
- **Direct Redirection**: Upon analysis, opens the Nonpartisan web portal with the multi-perspective breakdown and stakeholder spectrum.
- **Real-Time Backend Status Monitoring**: Actively checks backend health (`http://localhost:8000/health`) on load and displays an **Online**, **Offline**, or **Connecting** indicator in the popup header.
- **Graceful Error Handling**: Displays user-friendly error banners with one-click **Retry Connection** or **Try Again** actions if the backend service is offline, unreachable, or encounters an issue.

---

## Development & Build

All commands use [`pnpm`](https://pnpm.io/):

```bash
# Install dependencies
pnpm install

# Run extension in live development mode (auto-reloads upon changes)
pnpm dev

# Build production bundle (chrome-mv3)
pnpm build
```

---

## Loading in Chrome

1. Open Chrome and go to `chrome://extensions/`.
2. Toggle on **Developer mode** in the top right.
3. Click **Load unpacked**.
4. Select the build directory:
   ```text
   extension/.output/chrome-mv3
   ```
5. Pin the **Nonpartisan** extension icon to your browser toolbar.
