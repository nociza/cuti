# Cuti Web Architecture Proposal

## Current Refactoring Complete ✅

I've refactored the existing codebase to be more maintainable:

### 1. **Component Library** (`templates/components/ui_library.html`)
- Reusable Jinja2 macros for all UI components
- Consistent API for buttons, cards, forms, toggles, etc.
- Better taste in design with unified styling

### 2. **JavaScript Module System** (`static/js/cuti-components.js`)
- Single unified component library
- Event-driven architecture with EventBus
- Utility functions for common operations
- Auto-initialization of components
- Global API client with proper error handling

### 3. **Modular CSS** (`static/css/components.css`)
- Component-based styling
- Consistent design tokens
- Utility classes
- Responsive by default

### 4. **Example Refactored Page** (`templates/global_settings_refactored.html`)
- Shows how to use the new component system
- Much cleaner and more maintainable code
- Separation of concerns

## Proposed Modern Architecture

### Option 1: **Vite + Vue 3 + FastAPI** (Recommended)

This gives you modern DX while still being deployable with a single command.

#### Structure:
```
src/cuti/web/
├── backend/           # FastAPI backend
│   ├── api/          # API routes
│   ├── services/     # Business logic
│   └── models/       # Data models
├── frontend/         # Vue 3 frontend
│   ├── src/
│   │   ├── components/   # Vue components
│   │   ├── composables/  # Vue composables
│   │   ├── stores/       # Pinia stores
│   │   ├── views/        # Page components
│   │   └── main.js
│   ├── package.json
│   └── vite.config.js
└── pyproject.toml    # Single config for everything
```

#### Setup Script:
```python
# src/cuti/web/__main__.py
import subprocess
import os
from pathlib import Path

def setup_and_run():
    """Single command to run everything"""
    web_dir = Path(__file__).parent
    
    # Install frontend deps if needed
    frontend_dir = web_dir / "frontend"
    if not (frontend_dir / "node_modules").exists():
        subprocess.run(["npm", "install"], cwd=frontend_dir)
    
    # Run both frontend and backend
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    async def run_servers():
        with ThreadPoolExecutor() as executor:
            # Run Vite dev server
            vite = executor.submit(
                subprocess.run,
                ["npm", "run", "dev"],
                cwd=frontend_dir
            )
            
            # Run FastAPI
            from .backend.app import app
            import uvicorn
            await uvicorn.run(app, host="0.0.0.0", port=8000)
    
    asyncio.run(run_servers())

if __name__ == "__main__":
    setup_and_run()
```

#### Single Command:
```bash
uv run python -m cuti.web
```

### Option 2: **HTMX + Alpine.js + FastAPI** (Simpler)

Keep server-side rendering but add modern interactivity.

#### Benefits:
- No build step required
- Progressive enhancement
- Works without JavaScript
- Simpler mental model

#### Example Component:
```html
<!-- Using HTMX for dynamic updates -->
<div id="settings-form">
    <form hx-post="/api/settings" 
          hx-target="#settings-form" 
          hx-swap="outerHTML">
        
        <!-- Alpine.js for local state -->
        <div x-data="{ loading: false }">
            <button @click="loading = true" 
                    :disabled="loading">
                <span x-show="!loading">Save</span>
                <span x-show="loading">Saving...</span>
            </button>
        </div>
    </form>
</div>
```

### Option 3: **Preact + FastAPI** (Lightweight)

Preact is only 3KB and can be used without a build step:

```html
<script type="module">
import { h, render, useState } from 'https://esm.sh/preact@latest';
import htm from 'https://esm.sh/htm@latest';

const html = htm.bind(h);

function SettingsCard({ title, children }) {
    const [expanded, setExpanded] = useState(true);
    
    return html`
        <div class="card">
            <div class="card-header" onClick=${() => setExpanded(!expanded)}>
                <h3>${title}</h3>
            </div>
            ${expanded && html`<div class="card-content">${children}</div>`}
        </div>
    `;
}

// Mount components
document.querySelectorAll('[data-component="settings-card"]').forEach(el => {
    render(html`<${SettingsCard} title=${el.dataset.title} />`, el);
});
</script>
```

## Migration Path

### Phase 1: Current Refactoring ✅
- Component library
- Unified JavaScript
- Modular CSS

### Phase 2: Add Modern Tools
1. Add HTMX for dynamic updates
2. Keep Alpine.js for local state
3. Add Web Components for complex UI

### Phase 3: Optional Frontend Framework
- Only if complexity demands it
- Can be added incrementally
- Start with islands architecture

## Benefits of Current Refactoring

1. **Reduced Duplication**: Single source of truth for components
2. **Better Maintainability**: Clear separation of concerns
3. **Consistent Design**: Unified component library
4. **Better Performance**: Modular loading, smaller bundles
5. **Developer Experience**: Clear APIs, auto-initialization

## How to Use the New System

### In Templates:
```jinja2
{% import 'components/ui_library.html' as ui %}

{{ ui.button('Click Me', 'primary', '👍', 'handleClick()') }}

{% call ui.card('My Card', 'Subtitle', '📦') %}
    Card content here
{% endcall %}
```

### In JavaScript:
```javascript
// Use the global component system
$toast.success('Operation completed!');
$modal.open('settings-modal');

// Or use the full API
CutiComponents.components.DataTable(element, {
    data: myData,
    columns: [...]
});
```

### In CSS:
```html
<!-- Just use the utility classes -->
<div class="card card-elevated">
    <div class="card-header">
        <h3 class="card-title">Title</h3>
    </div>
    <div class="card-content p-3">
        <button class="btn btn-primary">Action</button>
    </div>
</div>
```

## Recommended Next Steps

1. **Immediate**: Start using the refactored component system in all pages
2. **Short-term**: Add HTMX for dynamic updates without full page reloads
3. **Medium-term**: Create Web Components for complex, reusable UI elements
4. **Long-term**: Consider Vue/React only if the app grows significantly in complexity

## Running with Single Command

The current system already works with:
```bash
uv run python -m cuti.web
```

For the proposed architectures, we can maintain this with a smart launcher that:
1. Checks for dependencies
2. Installs if needed (cached)
3. Runs all necessary services
4. Provides a unified interface

This keeps the developer experience simple while allowing for modern tooling.