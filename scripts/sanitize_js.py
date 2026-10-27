import json

json_path = 'logs/runs/run-b3d8e4ad_project.json'
with open(json_path, 'r', encoding='utf-8') as f:
    p = json.load(f)

for f in p['files']:
    if f['path'] == 'js/main.js':
        f['content'] = '''document.addEventListener('DOMContentLoaded', () => {
    const splitScreenLayout = new SplitScreenLayout();
    const markdownInput = new MarkdownInput('markdown-input');
    const htmlPreview = new HtmlPreview('html-preview');
    const statusBar = new StatusBar('word-count', 'char-count');
    const formattingToolbar = new FormattingToolbar(markdownInput);
    const themeManager = new ThemeManager();

    const initialMarkdown = "# Welcome to Markdown Live Preview!\\n\\nThis is a **live preview** editor with styled typography.\\n\\n### Features:\\n- Real-time markdown rendering\\n- *Italic* and **Bold** formatting\\n- Split-screen dark theme\\n- Character and word counter\\n\\n```javascript\\nconsole.log('DevAgents is fully working!');\\n```";
    markdownInput.setValue(initialMarkdown);
    updatePreviewAndCounts(initialMarkdown);

    markdownInput.onInput((currentMarkdown) => {
        updatePreviewAndCounts(currentMarkdown);
    });

    function updatePreviewAndCounts(markdownText) {
        const html = parseMarkdown(markdownText);
        htmlPreview.render(html);
        const { wordCount, charCount } = calculateCounts(markdownText);
        statusBar.updateCounts(wordCount, charCount);
    }
});
'''
    elif f['path'] == 'js/components/FormattingToolbar.js':
        f['content'] = '''/**
 * Manages the formatting toolbar and its buttons.
 */
class FormattingToolbar {
    constructor(markdownInputInstance) {
        this.markdownInput = markdownInputInstance;
        this.setupButtons();
    }

    setupButtons() {
        const boldBtn = document.getElementById('bold-btn');
        const italicBtn = document.getElementById('italic-btn');
        const h1Btn = document.getElementById('h1-btn');
        const h2Btn = document.getElementById('h2-btn');
        const h3Btn = document.getElementById('h3-btn');
        const codeBlockBtn = document.getElementById('code-block-btn');

        if (boldBtn) boldBtn.addEventListener('click', () => this.markdownInput.wrapSelection('**', '**'));
        if (italicBtn) italicBtn.addEventListener('click', () => this.markdownInput.wrapSelection('*', '*'));
        if (h1Btn) h1Btn.addEventListener('click', () => this.applyHeading('# '));
        if (h2Btn) h2Btn.addEventListener('click', () => this.applyHeading('## '));
        if (h3Btn) h3Btn.addEventListener('click', () => this.applyHeading('### '));
        if (codeBlockBtn) codeBlockBtn.addEventListener('click', () => this.markdownInput.wrapSelection('```\\n', '\\n```'));
    }

    applyHeading(level) {
        const start = this.markdownInput.textarea.selectionStart;
        const lines = this.markdownInput.getValue().split('\\n');
        const currentLineIndex = this.markdownInput.getValue().substring(0, start).split('\\n').length - 1;
        const currentLineText = lines[currentLineIndex];

        if (currentLineText.startsWith('#')) {
            lines[currentLineIndex] = currentLineText.replace(/^#+\\s*/, level);
        } else {
            lines[currentLineIndex] = level + currentLineText;
        }
        this.markdownInput.setValue(lines.join('\\n'));
        this.markdownInput.textarea.focus();
        this.markdownInput.textarea.dispatchEvent(new Event('input', { bubbles: true }));
    }
}
'''

with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(p, f, indent=2)

print('Sanitized main.js and FormattingToolbar.js successfully!')
