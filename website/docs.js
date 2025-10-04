// Documentation content loader
const docs = {
    'automatic-tools-activation': 'docs/automatic-tools-activation.md',
    'claude-account-quick-start': 'docs/claude-account-quick-start.md',
    'claude-account-switching': 'docs/claude-account-switching.md',
    'claude-api-keys': 'docs/claude-api-keys.md',
    'claude-container-auth': 'docs/claude-container-auth.md',
    'cli-tools-management': 'docs/cli-tools-management.md',
    'container-status-command': 'docs/container-status-command.md',
    'container': 'docs/container.md',
    'devcontainer': 'docs/devcontainer.md',
    'rate-limit-handling': 'docs/rate-limit-handling.md',
    'todo-system': 'docs/todo-system.md',
    'workspace-tools-architecture': 'docs/workspace-tools-architecture.md'
};

// Configure marked.js
marked.setOptions({
    highlight: function(code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            try {
                return hljs.highlight(code, { language: lang }).value;
            } catch (err) {}
        }
        return hljs.highlightAuto(code).value;
    },
    breaks: true,
    gfm: true
});

// Load documentation
async function loadDoc(docName) {
    const docContent = document.getElementById('doc-content');
    const docPath = docs[docName];

    if (!docPath) {
        docContent.innerHTML = `
            <div style="text-align: center; padding: 4rem;">
                <i class="fas fa-file-circle-question" style="font-size: 4rem; color: var(--text-light); margin-bottom: 1rem;"></i>
                <h2>Documentation not found</h2>
                <p style="color: var(--text-light);">The requested documentation could not be found.</p>
            </div>
        `;
        return;
    }

    // Show loading
    docContent.innerHTML = `
        <div class="loading">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Loading documentation...</p>
        </div>
    `;

    try {
        const response = await fetch(docPath);
        if (!response.ok) {
            throw new Error('Failed to load documentation');
        }
        
        const markdown = await response.text();
        const html = marked.parse(markdown);
        docContent.innerHTML = html;

        // Convert markdown links to proper doc viewer URLs
        convertMarkdownLinks();

        // Add copy buttons to code blocks
        addCopyButtons();

        // Update active nav link
        updateActiveNavLink(docName);

        // Update page title
        updatePageTitle(docName);

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
        console.error('Error loading documentation:', error);
        docContent.innerHTML = `
            <div style="text-align: center; padding: 4rem;">
                <i class="fas fa-circle-exclamation" style="font-size: 4rem; color: #EF4444; margin-bottom: 1rem;"></i>
                <h2>Error loading documentation</h2>
                <p style="color: var(--text-light);">Could not load the documentation. Please try again later.</p>
                <p style="color: var(--text-light); font-size: 0.875rem; margin-top: 1rem;">Error: ${error.message}</p>
            </div>
        `;
    }
}

// Convert markdown links (.md) to proper doc viewer URLs
function convertMarkdownLinks() {
    const docContent = document.getElementById('doc-content');
    const links = docContent.querySelectorAll('a[href]');
    
    links.forEach(link => {
        const href = link.getAttribute('href');
        
        // Check if it's a markdown file link
        if (href && href.endsWith('.md')) {
            // Extract filename without extension
            const filename = href.replace(/^.*\//, '').replace(/\.md$/, '');
            
            // Check if this doc exists in our docs object
            if (docs[filename]) {
                // Convert to doc viewer URL
                link.setAttribute('href', `docs.html?doc=${filename}`);
                
                // Add click handler to load without page reload
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    
                    // Update URL
                    const url = new URL(window.location);
                    url.searchParams.set('doc', filename);
                    window.history.pushState({}, '', url);
                    
                    // Load the doc
                    loadDoc(filename);
                });
            }
        }
        // Handle relative links to docs folder
        else if (href && href.match(/docs\/.*\.md$/)) {
            const filename = href.replace(/^.*\//, '').replace(/\.md$/, '');
            
            if (docs[filename]) {
                link.setAttribute('href', `docs.html?doc=${filename}`);
                
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    const url = new URL(window.location);
                    url.searchParams.set('doc', filename);
                    window.history.pushState({}, '', url);
                    loadDoc(filename);
                });
            }
        }
    });
}

// Update page title based on current doc
function updatePageTitle(docName) {
    // Convert doc name to title case
    const title = docName
        .split('-')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
    
    document.title = `${title} - Cuti Documentation`;
}

// Add copy buttons to code blocks
function addCopyButtons() {
    const codeBlocks = document.querySelectorAll('#doc-content pre code');
    codeBlocks.forEach(codeBlock => {
        const pre = codeBlock.parentElement;
        
        // Wrap in container if not already wrapped
        if (!pre.parentElement.classList.contains('code-block-wrapper')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'code-block-wrapper';
            wrapper.style.position = 'relative';
            pre.parentElement.insertBefore(wrapper, pre);
            wrapper.appendChild(pre);
        }

        // Add copy button
        const button = document.createElement('button');
        button.className = 'doc-copy-btn';
        button.innerHTML = '<i class="fas fa-copy"></i>';
        button.style.cssText = `
            position: absolute;
            top: 0.5rem;
            right: 0.5rem;
            background: var(--primary-color);
            color: white;
            border: none;
            padding: 0.5rem 0.75rem;
            border-radius: 0.25rem;
            cursor: pointer;
            font-size: 0.875rem;
            transition: background 0.3s;
        `;

        button.addEventListener('click', () => {
            const text = codeBlock.textContent;
            navigator.clipboard.writeText(text).then(() => {
                button.innerHTML = '<i class="fas fa-check"></i>';
                button.style.background = '#10B981';
                setTimeout(() => {
                    button.innerHTML = '<i class="fas fa-copy"></i>';
                    button.style.background = '';
                }, 2000);
            });
        });

        button.addEventListener('mouseenter', () => {
            button.style.background = 'var(--primary-dark)';
        });

        button.addEventListener('mouseleave', () => {
            if (button.innerHTML.includes('fa-copy')) {
                button.style.background = 'var(--primary-color)';
            }
        });

        pre.parentElement.appendChild(button);
    });
}

// Update active navigation link
function updateActiveNavLink(docName) {
    const navLinks = document.querySelectorAll('.docs-nav .nav-link');
    navLinks.forEach(link => {
        if (link.getAttribute('data-doc') === docName) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

// Handle navigation clicks
document.addEventListener('DOMContentLoaded', () => {
    const navLinks = document.querySelectorAll('.docs-nav .nav-link');
    
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const docName = link.getAttribute('data-doc');
            
            // Update URL without reloading
            const url = new URL(window.location);
            url.searchParams.set('doc', docName);
            window.history.pushState({}, '', url);
            
            loadDoc(docName);
        });
    });

    // Load initial documentation
    const urlParams = new URLSearchParams(window.location.search);
    const initialDoc = urlParams.get('doc') || 'claude-account-quick-start';
    loadDoc(initialDoc);

    // Handle browser back/forward
    window.addEventListener('popstate', () => {
        const urlParams = new URLSearchParams(window.location.search);
        const docName = urlParams.get('doc') || 'claude-account-quick-start';
        loadDoc(docName);
    });
});

