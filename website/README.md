# Cuti Static Website

A beautiful, modern static website for Cuti documentation and project information.

## Features

- 🎨 Modern, responsive design
- 📚 Interactive documentation viewer
- 🔍 Real-time markdown rendering
- 📱 Mobile-friendly interface
- ⚡ Fast and lightweight
- 🎯 Easy to host anywhere

## Local Development

### Quick Start (from root directory)

Use the convenient `just` commands from the project root:

```bash
# Build and validate the website
just website-build

# Serve the website locally
just website-serve

# Then open http://localhost:8000 in your browser
```

### Alternative: Manual Setup

You can also serve the website directly:

```bash
# Navigate to the website directory
cd website

# Run build script
./build.sh

# Serve using npx (recommended)
npx -y http-server -p 8000

# Or using Python
python3 -m http.server 8000
```

Then open your browser to http://localhost:8000

## Deployment

### GitHub Pages

```bash
# From project root
just website-deploy-github
```

### Netlify / Vercel / Cloudflare Pages

Connect your Git repo and use these settings:

```
Build command: cd website && ./build.sh
Output directory: website
```

That's it! The `build.sh` script syncs docs automatically.

## File Structure

```
website/
├── index.html          # Home page
├── docs.html           # Documentation viewer
├── styles.css          # All styles
├── script.js           # Home page scripts
├── docs.js             # Documentation loader
├── build.sh            # Build script (syncs docs)
├── serve.py            # Local dev server
├── favicon.svg         # Site icon
└── README.md           # This file
```

## Updating Documentation

### Single Source of Truth

Documentation lives in the **root `docs/` folder only**. The `website/docs/` folder is:
- ✅ **Generated at build time** (not committed to git)
- ✅ **Automatically synced** by build/serve/deploy commands
- ✅ **Listed in `.gitignore`**

### Workflow

```bash
# 1. Edit documentation in root docs/ folder (single source of truth)
vim docs/my-doc.md

# 2. Test locally (auto-syncs docs)
just website-serve

# 3. Deploy (auto-syncs docs)
just website-deploy-github
```

**All commands automatically sync docs** by running `build.sh`.

### Adding New Documentation

1. Add your `.md` file to the root `docs/` folder
2. Update the `docs` object in `docs.js` to include the new file
3. Add a navigation link in `docs.html` sidebar
4. Run `just website-serve` to test (auto-syncs)

## Customization

### Colors

Edit CSS variables in `styles.css`:

```css
:root {
    --primary-color: #4F46E5;
    --primary-dark: #4338CA;
    --secondary-color: #10B981;
    /* ... */
}
```

### Navigation

Edit the navigation links in both `index.html` and `docs.html`.

### Content

- Home page content: Edit `index.html`
- Documentation list: Edit `docs.js`

## Technologies Used

- HTML5
- CSS3 (with CSS Grid and Flexbox)
- Vanilla JavaScript
- [Marked.js](https://marked.js.org/) - Markdown parser
- [Highlight.js](https://highlightjs.org/) - Syntax highlighting
- [Font Awesome](https://fontawesome.com/) - Icons

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers

## License

Same as the main Cuti project - Apache 2.0

