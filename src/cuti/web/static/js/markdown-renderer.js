/**
 * Enhanced Markdown Renderer for Terminal Output
 * Provides proper markdown rendering with syntax highlighting
 */

class MarkdownRenderer {
    constructor() {
        // Code language aliases
        this.languageAliases = {
            'js': 'javascript',
            'ts': 'typescript',
            'py': 'python',
            'rb': 'ruby',
            'yml': 'yaml',
            'sh': 'bash',
            'shell': 'bash'
        };
    }

    /**
     * Render markdown to HTML with proper formatting
     */
    render(markdown) {
        if (!markdown) return '';
        
        let html = markdown;
        
        // Process in order: code blocks first, then inline elements
        html = this.renderCodeBlocks(html);
        html = this.renderHeaders(html);
        html = this.renderLists(html);
        html = this.renderBlockquotes(html);
        html = this.renderTables(html);
        html = this.renderHorizontalRules(html);
        html = this.renderLinks(html);
        html = this.renderImages(html);
        html = this.renderBold(html);
        html = this.renderItalic(html);
        html = this.renderInlineCode(html);
        html = this.renderLineBreaks(html);
        
        return html;
    }

    /**
     * Render code blocks with syntax highlighting
     */
    renderCodeBlocks(text) {
        // Match fenced code blocks with optional language
        const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
        
        return text.replace(codeBlockRegex, (match, language, code) => {
            language = language || 'plaintext';
            language = this.languageAliases[language] || language;
            
            // Escape HTML in code
            const escapedCode = this.escapeHtml(code.trim());
            
            return `<div class="code-block-wrapper">
                <div class="code-block-header">
                    <span class="code-language">${language}</span>
                    <button class="copy-code-btn" onclick="copyCode(this)" title="Copy code">
                        <i class="fas fa-copy"></i>
                    </button>
                </div>
                <pre class="code-block language-${language}"><code>${escapedCode}</code></pre>
            </div>`;
        });
    }

    /**
     * Render headers (H1-H6)
     */
    renderHeaders(text) {
        // H6 to H1 (process smaller headers first)
        for (let level = 6; level >= 1; level--) {
            const regex = new RegExp(`^${'#'.repeat(level)} (.+)$`, 'gm');
            text = text.replace(regex, `<h${level} class="markdown-header">$1</h${level}>`);
        }
        return text;
    }

    /**
     * Render unordered and ordered lists
     */
    renderLists(text) {
        // Unordered lists
        text = text.replace(/^\* (.+)$/gm, '<li>$1</li>');
        text = text.replace(/^- (.+)$/gm, '<li>$1</li>');
        text = text.replace(/^\+ (.+)$/gm, '<li>$1</li>');
        
        // Wrap consecutive li elements in ul
        text = text.replace(/(<li>.*<\/li>\n?)+/g, (match) => {
            return `<ul class="markdown-list">${match}</ul>`;
        });
        
        // Ordered lists
        text = text.replace(/^\d+\. (.+)$/gm, '<li class="ordered">$1</li>');
        
        // Wrap consecutive ordered li elements in ol
        text = text.replace(/(<li class="ordered">.*<\/li>\n?)+/g, (match) => {
            const cleaned = match.replace(/ class="ordered"/g, '');
            return `<ol class="markdown-list">${cleaned}</ol>`;
        });
        
        return text;
    }

    /**
     * Render blockquotes
     */
    renderBlockquotes(text) {
        return text.replace(/^> (.+)$/gm, '<blockquote class="markdown-blockquote">$1</blockquote>');
    }

    /**
     * Render tables
     */
    renderTables(text) {
        const tableRegex = /\|(.+)\|[\r\n]+\|[-:\s|]+\|[\r\n]+((?:\|.+\|[\r\n]*)+)/g;
        
        return text.replace(tableRegex, (match, header, body) => {
            const headers = header.split('|').filter(h => h.trim());
            const rows = body.trim().split('\n').map(row => 
                row.split('|').filter(cell => cell !== undefined && cell !== '')
            );
            
            let table = '<table class="markdown-table">';
            
            // Header
            table += '<thead><tr>';
            headers.forEach(h => {
                table += `<th>${h.trim()}</th>`;
            });
            table += '</tr></thead>';
            
            // Body
            table += '<tbody>';
            rows.forEach(row => {
                table += '<tr>';
                row.forEach(cell => {
                    table += `<td>${cell.trim()}</td>`;
                });
                table += '</tr>';
            });
            table += '</tbody></table>';
            
            return table;
        });
    }

    /**
     * Render horizontal rules
     */
    renderHorizontalRules(text) {
        return text.replace(/^(-{3,}|_{3,}|\*{3,})$/gm, '<hr class="markdown-hr">');
    }

    /**
     * Render links
     */
    renderLinks(text) {
        // [text](url)
        text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, 
            '<a href="$2" class="markdown-link" target="_blank" rel="noopener">$1</a>');
        
        // Autolink URLs
        text = text.replace(/(https?:\/\/[^\s<]+)/g, 
            '<a href="$1" class="markdown-link" target="_blank" rel="noopener">$1</a>');
        
        return text;
    }

    /**
     * Render images
     */
    renderImages(text) {
        return text.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, 
            '<img src="$2" alt="$1" class="markdown-image">');
    }

    /**
     * Render bold text
     */
    renderBold(text) {
        // **text** or __text__
        text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        text = text.replace(/__([^_]+)__/g, '<strong>$1</strong>');
        return text;
    }

    /**
     * Render italic text
     */
    renderItalic(text) {
        // *text* or _text_ (but not within words)
        text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        text = text.replace(/\b_([^_]+)_\b/g, '<em>$1</em>');
        return text;
    }

    /**
     * Render inline code
     */
    renderInlineCode(text) {
        return text.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
    }

    /**
     * Render line breaks
     */
    renderLineBreaks(text) {
        return text.replace(/\n/g, '<br>');
    }

    /**
     * Escape HTML characters
     */
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
}

// Copy code function
function copyCode(button) {
    const codeBlock = button.closest('.code-block-wrapper').querySelector('code');
    const text = codeBlock.textContent;
    
    navigator.clipboard.writeText(text).then(() => {
        const icon = button.querySelector('i');
        icon.className = 'fas fa-check';
        button.style.color = '#10b981';
        
        setTimeout(() => {
            icon.className = 'fas fa-copy';
            button.style.color = '';
        }, 2000);
    });
}

// Export for use
window.MarkdownRenderer = MarkdownRenderer;