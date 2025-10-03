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

# Serve using Python 3
python3 -m http.server 8000

# Or use the custom server script
python3 serve.py
```

Then open your browser to http://localhost:8000

### Alternative: Using Node.js

If you have Node.js installed, you can use `http-server`:

```bash
# Install http-server globally (one time only)
npm install -g http-server

# Serve the website
http-server -p 8000
```

## Deployment

### Quick Deploy (from root directory)

```bash
# Interactive deployment (choose your platform)
just website-deploy

# Deploy directly to GitHub Pages
just website-deploy-github

# View deployment instructions for other platforms
just website-deploy-manual
```

## Hosting Options

This is a static website that can be hosted on any static hosting service:

### GitHub Pages

1. Push the `website` folder to your repository
2. Go to Settings → Pages
3. Select the branch and `/website` folder
4. Your site will be live at `https://yourusername.github.io/cuti/`

### Netlify

1. Connect your repository
2. Set build directory to `website`
3. Deploy!

### Vercel

1. Import your repository
2. Set output directory to `website`
3. Deploy!

### Other Options

The website works on:
- AWS S3 + CloudFront
- Google Cloud Storage
- Azure Static Web Apps
- Cloudflare Pages
- Surge.sh
- Firebase Hosting
- Any static hosting provider

## File Structure

```
website/
├── index.html          # Home page
├── docs.html           # Documentation viewer
├── styles.css          # All styles
├── script.js           # Home page scripts
├── docs.js             # Documentation loader
└── README.md           # This file
```

## Updating Documentation

The website automatically loads documentation from the `../docs/` folder. To add new documentation:

1. Add your `.md` file to the `docs/` folder
2. Update the `docs` object in `docs.js` to include the new file
3. Add a navigation link in `docs.html` sidebar

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

