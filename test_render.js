import fs from 'fs';

function renderMarkdownToUI(md) {
    let lines = md.split('\n');
    let html = '';
    
    // Remove warning blocks
    md = md.replace(/\[!WARNING\]\s*/gi, '');
    lines = md.split('\n');

    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        if (!line) continue;

        // Horizontal rules
        if (line.match(/^---+$/) || line.match(/^\*\*\*+$/)) {
            html += `<hr style="border: 0; border-top: 1px solid var(--border-neutral); margin: 2rem 0;">`;
            continue;
        }

        // Main Finding Heading: ## Finding X – Title
        let findingMatch = line.match(/^##\s+(Finding\s+\d+)[\s:–-]+(.*)/i);
        if (findingMatch) {
            html += `<div style="margin-bottom: 1.5rem;">
                        <div style="font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; margin-bottom: 0.25rem;">${findingMatch[1]}</div>
                        <h3 style="font-size: 1.25rem; font-weight: 700; color: var(--text-main); margin: 0;">${findingMatch[2].replace(/\*\*/g, '')}</h3>
                     </div>`;
            continue;
        }

        // Subsections (## Title or ### Title or **Title**)
        let genericHeading = line.match(/^(#{2,3})\s+(.*)/);
        let boldHeading = line.match(/^\*\*(.*)\*\*:?$/);
        
        let headingText = '';
        if (genericHeading) headingText = genericHeading[2];
        else if (boldHeading) headingText = boldHeading[1];

        if (headingText) {
            // Remove asterisks if they leaked
            headingText = headingText.replace(/\*\*/g, '');
            html += `<div style="font-size: 0.95rem; font-weight: 600; color: var(--accent-primary); margin-top: 1.5rem; margin-bottom: 0.5rem; letter-spacing: 0.02em;">${headingText}</div>`;
            continue;
        }

        // Quotes
        if (line.startsWith('>')) {
            let quote = line.substring(1).trim().replace(/^["']|["']$/g, '');
            html += `<div style="border-left: 3px solid var(--border-neutral); background-color: rgba(255,255,255,0.02); padding: 1rem 1.25rem; margin: 1rem 0; border-radius: 0 0.5rem 0.5rem 0; font-style: italic; color: #e5e7eb;">“${quote}”</div>`;
            continue;
        }

        // Source ID / Record ID
        let sourceMatch = line.match(/(Source|Record ID):\s*(.+)/i);
        if (sourceMatch) {
            html += `<div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1rem; word-break: break-all;">Source: ${sourceMatch[2]}</div>`;
            continue;
        }

        // Bullets
        let bulletMatch = line.match(/^[-*]\s+(.*)/);
        if (bulletMatch) {
            let text = bulletMatch[1].replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            html += `<div style="display: flex; gap: 0.5rem; margin-bottom: 0.5rem; color: #d1d5db;"><span style="color: var(--accent-primary);">•</span><span>${text}</span></div>`;
            continue;
        }

        // Numbered lists
        let numMatch = line.match(/^(\d+)\.\s+(.*)/);
        if (numMatch) {
            let text = numMatch[2].replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            html += `<div style="display: flex; gap: 0.5rem; margin-bottom: 0.5rem; color: #d1d5db;"><span style="color: var(--text-muted);">${numMatch[1]}.</span><span>${text}</span></div>`;
            continue;
        }

        // Paragraphs
        line = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html += `<p style="color: #d1d5db; line-height: 1.6; margin-bottom: 1rem;">${line}</p>`;
    }
    return html;
}

let data = JSON.parse(fs.readFileSync('api_resp.json', 'utf8'));
console.log(renderMarkdownToUI(data.analysis.markdown_analysis));
