function setQuery(text) {
    document.getElementById('query-input').value = text.replace(/"/g, '');
    runDiscovery();
}

function handleEnter(e) {
    if (e.key === 'Enter') {
        runDiscovery();
    }
}

async function renderCharts() {
    // Charts removed
}

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
            text = text.replace(/`(.*?)`/g, '<span style="background-color: rgba(217, 70, 239, 0.15); color: var(--accent-primary); padding: 0.15rem 0.4rem; border-radius: 0.25rem; font-family: monospace; font-size: 0.85em;">$1</span>');
            html += `<div style="display: flex; gap: 0.5rem; margin-bottom: 0.5rem; color: #d1d5db;"><span style="color: var(--accent-primary);">•</span><span>${text}</span></div>`;
            continue;
        }

        // Numbered lists
        let numMatch = line.match(/^(\d+)\.\s+(.*)/);
        if (numMatch) {
            let text = numMatch[2].replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            text = text.replace(/`(.*?)`/g, '<span style="background-color: rgba(217, 70, 239, 0.15); color: var(--accent-primary); padding: 0.15rem 0.4rem; border-radius: 0.25rem; font-family: monospace; font-size: 0.85em;">$1</span>');
            html += `<div style="display: flex; gap: 0.5rem; margin-bottom: 0.5rem; color: #d1d5db;"><span style="color: var(--text-muted);">${numMatch[1]}.</span><span>${text}</span></div>`;
            continue;
        }

        // Tables
        let tableMatch = line.match(/^\|(.+)/);
        if (tableMatch) {
            let isHeaderDivider = line.match(/^\|[\s\-:|]+$/) || line.match(/^\|[\s\-:|]+\|$/);
            if (isHeaderDivider) {
                // If it's a divider row, we might need to close a thead.
                // For simplicity, we just skip it or handle it in the next pass.
                continue;
            }
            
            // Remove trailing pipe if it exists, then split
            let rawCells = tableMatch[1].replace(/\|$/, '');
            let cells = rawCells.split('|').map(c => {
                let txt = c.trim().replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                return txt.replace(/`(.*?)`/g, '<span style="background-color: rgba(217, 70, 239, 0.15); color: var(--accent-primary); padding: 0.15rem 0.4rem; border-radius: 0.25rem; font-family: monospace; font-size: 0.85em;">$1</span>');
            });
            
            // Check if this is the start of a table
            let prevLine = i > 0 ? lines[i-1].trim() : '';
            let isFirstRow = !prevLine.startsWith('|');
            
            if (isFirstRow) {
                html += `<div style="overflow-x: auto; margin: 1rem 0; border-radius: 0.5rem; border: 1px solid var(--border-neutral);">`;
                html += `<table style="width: 100%; border-collapse: collapse; text-align: left;">`;
                html += `<thead style="background-color: rgba(255,255,255,0.05); border-bottom: 1px solid var(--border-neutral);"><tr>`;
                cells.forEach(cell => {
                    html += `<th style="padding: 0.75rem 1rem; font-size: 0.85rem; color: var(--text-muted); font-weight: 600;">${cell}</th>`;
                });
                html += `</tr></thead><tbody>`;
            } else {
                html += `<tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">`;
                cells.forEach(cell => {
                    html += `<td style="padding: 0.75rem 1rem; font-size: 0.9rem; color: #d1d5db;">${cell}</td>`;
                });
                html += `</tr>`;
            }

            // Check if this is the end of a table
            let nextLine = i < lines.length - 1 ? lines[i+1].trim() : '';
            if (!nextLine.startsWith('|')) {
                html += `</tbody></table></div>`;
            }
            continue;
        }

        // Paragraphs
        line = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        line = line.replace(/`(.*?)`/g, '<span style="background-color: rgba(217, 70, 239, 0.15); color: var(--accent-primary); padding: 0.15rem 0.4rem; border-radius: 0.25rem; font-family: monospace; font-size: 0.85em;">$1</span>');
        html += `<p style="color: #d1d5db; line-height: 1.6; margin-bottom: 1rem;">${line}</p>`;
    }
    return html;
}

document.addEventListener('DOMContentLoaded', () => {
    renderCharts();
});

async function runDiscovery() {
    const input = document.getElementById('query-input');
    const query = input.value.trim();
    if (!query) return;

    const staticInsights = document.getElementById('static-insights');
    const resultsContainer = document.getElementById('results-container');
    const loadingState = document.getElementById('loading-state');
    const insightCard = document.getElementById('insight-card');
    const insightContent = document.getElementById('insight-content');

    if (staticInsights) staticInsights.classList.add('hidden');
    resultsContainer.classList.remove('hidden');
    loadingState.classList.remove('hidden');
    insightCard.classList.add('hidden');

    try {
        const res = await fetch('/ask', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ question: query })
        });
        const data = await res.json();
        
        // 1. Evidence Summary (Removed per user request)
        


        // 2. Insight Summary
        if (data.analysis) {
            console.log("Markdown analysis received:", data.analysis.markdown_analysis);
            if (data.analysis.markdown_analysis) {
                const finalHtml = renderMarkdownToUI(data.analysis.markdown_analysis);
                console.log("Rendered HTML:", finalHtml);
                insightContent.innerHTML = finalHtml || '<p>No insights were generated by the model.</p>';
            } else {

                // fallback for JSON structure if needed
                let htmlContent = `
                    <h3>Key Findings</h3>
                    <ul>${(data.analysis.key_findings || []).map(f => `<li>${f}</li>`).join('')}</ul>
                    <h3>Supporting Evidence</h3>
                    <ul>${(data.analysis.supporting_evidence || []).map(e => `<li>${e}</li>`).join('')}</ul>
                    <h3>Evidence Gaps</h3>
                    <ul>${(data.analysis.evidence_gaps || []).map(g => `<li>${g}</li>`).join('')}</ul>
                    <h3>Confidence</h3>
                    <p>${data.analysis.confidence || ''}</p>
                `;
                insightContent.innerHTML = htmlContent;
            }
        }
        
        loadingState.classList.add('hidden');
        insightCard.classList.remove('hidden');
    } catch (err) {
        loadingState.classList.add('hidden');
        insightCard.classList.remove('hidden');
        insightContent.innerHTML = `<p style="color: #ef4444">An error occurred while generating insights.</p>`;
    }
}
