// State configurations
let currentPlatform = 'youtube';
let currentCategory = '📹 Video/Audio Only';
let analyzedData = null;

// Categories for each platform
const platformCategories = {
    youtube: [
        '📹 Video/Audio Only',
        '🖼️ Cover Thumbnail'
    ],
    instagram: [
        '📹 Video/Reel',
        '🖼️ Photo/Carousel',
        '📱 Story',
        '👤 Profile Pic'
    ]
};

// URL inputs placeholders
const inputPlaceholders = {
    '📹 Video/Audio Only': 'Paste YouTube link here...',
    '🖼️ Cover Thumbnail': 'Paste YouTube link here...',
    '📹 Video/Reel': 'Paste Instagram Reel or Video link...',
    '🖼️ Photo/Carousel': 'Paste Instagram Carousel Post link...',
    '📱 Story': 'Paste Instagram Story link...',
    '👤 Profile Pic': 'Paste Instagram Profile URL or @username...'
};

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    switchPlatform('youtube');
    log('Velocity web dashboard loaded.');
    
    // Auto paste detection
    const urlInput = document.getElementById('url-input');
    urlInput.addEventListener('keyup', (e) => {
        const val = e.target.value.trim().toLowerCase();
        if (val.includes('youtube.com') || val.includes('youtu.be')) {
            if (currentPlatform !== 'youtube') {
                switchPlatform('youtube');
            }
        } else if (val.includes('instagram.com')) {
            if (currentPlatform !== 'instagram') {
                switchPlatform('instagram');
            }
        }
    });

    // Animate URLs input focus events
    urlInput.addEventListener('focus', () => log('Awaiting user input target url...'));
});

// Switch Main Tabs (Downloader / Settings / Logs)
function switchMainTab(tabName) {
    // Buttons
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`tab-btn-${tabName}`).classList.add('active');

    // Panes
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(`tab-content-${tabName}`).classList.add('active');

    log(`Tab panel active context target: ${tabName}`);
}

// Switch Platforms (YouTube / Instagram)
function switchPlatform(platform) {
    currentPlatform = platform;
    
    // Update platform button states
    document.getElementById('platform-btn-yt').classList.toggle('active', platform === 'youtube');
    document.getElementById('platform-btn-ig').classList.toggle('active', platform === 'instagram');

    // Load category choices
    const container = document.getElementById('category-selector');
    container.innerHTML = '';

    platformCategories[platform].forEach(cat => {
        const btn = document.createElement('button');
        btn.className = `seg-btn${currentCategory === cat ? ' active' : ''}`;
        btn.innerText = cat;
        btn.onclick = () => selectCategory(cat, btn);
        container.appendChild(btn);
    });

    // Make sure we select the first one
    const firstCat = platformCategories[platform][0];
    selectCategory(firstCat, container.firstChild);
    log(`Platform swop context: ${platform === 'youtube' ? 'YouTube' : 'Instagram'}`);
}

// Select Category
function selectCategory(category, buttonElement) {
    currentCategory = category;
    
    // Segment styling swap
    document.querySelectorAll('.category-choices .seg-btn').forEach(btn => btn.classList.remove('active'));
    if (buttonElement) buttonElement.classList.add('active');

    // Input placeholder update
    const urlInput = document.getElementById('url-input');
    urlInput.placeholder = inputPlaceholders[category] || 'Paste URL link here...';

    // Hide formats selector if not download quality video stream
    const optionsRow = document.getElementById('stream-options-row');
    if (category === '📹 Video/Audio Only' || category === '📹 Video/Reel') {
        optionsRow.classList.remove('hidden');
    } else {
        optionsRow.classList.add('hidden');
    }

    // Update main action download button label
    const downloadBtn = document.getElementById('download-btn');
    if (category === '📱 Story') {
        downloadBtn.innerText = 'Download Slides';
    } else if (category === '🖼️ Photo/Carousel') {
        downloadBtn.innerText = 'Download Selected';
    } else if (category === '👤 Profile Pic') {
        downloadBtn.innerText = 'Download Profile Pic';
    } else if (category === '🖼️ Cover Thumbnail') {
        downloadBtn.innerText = 'Download Thumbnail';
    } else {
        downloadBtn.innerText = 'Download Video';
    }

    // Clear previews when switching categories
    document.getElementById('preview-card').classList.add('hidden');
    document.getElementById('picker-card').classList.add('hidden');
    analyzedData = null;

    log(`Category modified: ${category}`);
}

// Log utility
function log(msg) {
    const consoleBox = document.getElementById('console-output');
    const timestamp = new Date().toLocaleTimeString();
    consoleBox.innerHTML += `\n[${timestamp}] ${msg}`;
    consoleBox.scrollTop = consoleBox.scrollHeight;
    console.log(`[${timestamp}] ${msg}`);
}

// Update Footer Status
function updateStatus(msg, type = 'online') {
    const dot = document.getElementById('footer-dot');
    const txt = document.getElementById('footer-status-text');
    txt.innerText = msg;
    
    dot.className = 'status-dot';
    if (type === 'error') {
        dot.style.color = '#EF4444';
    } else if (type === 'processing') {
        dot.style.color = '#3b82f6';
    } else {
        dot.style.color = '#B6FF00';
    }
}

// Analyze URL Backend Request
async function analyzeUrl() {
    const urlInput = document.getElementById('url-input');
    const url = urlInput.value.trim();
    if (!url) {
        updateStatus('Enter a URL first.', 'error');
        log('Analysis error: target URL empty.');
        return;
    }

    const analyzeBtn = document.getElementById('analyze-btn');
    analyzeBtn.disabled = true;
    analyzeBtn.innerText = 'Analyzing...';
    updateStatus('Parsing media details...', 'processing');
    log(`Inbound target URL pipeline active: ${url}`);

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url, category: currentCategory })
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Extract error occurred');
        }

        const data = await response.json();
        analyzedData = data;
        renderPreview(data);
        updateStatus('Ready to download.', 'online');
        log(`Metadata extracted successfully: '${data.title.substring(0, 30)}...'`);

    } catch (e) {
        updateStatus('Analysis failed.', 'error');
        log(`Parsing extraction error details: ${e.message}`);
        alert(`Analysis Error: ${e.message}`);
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.innerText = 'Analyze URL';
    }
}

// Render Preview Meta Card
function renderPreview(data) {
    const previewCard = document.getElementById('preview-card');
    previewCard.classList.remove('hidden');

    // Title
    const titleLbl = document.getElementById('media-title');
    titleLbl.innerText = data.title;

    // Channel & Duration
    document.getElementById('media-channel').innerText = `Channel: ${data.channel}`;
    document.getElementById('media-duration').innerText = `Duration: ${data.duration}`;

    // Thumbnail Preview rendering
    const thumbContainer = document.getElementById('preview-thumbnail');
    if (data.thumbnail) {
        thumbContainer.innerHTML = `<img src="${data.thumbnail}" class="thumbnail-image" alt="Preview">`;
    } else {
        thumbContainer.innerHTML = 'Metadata Preview';
    }

    // Picker list slides checkboxes setup (playlist / story elements)
    const pickerCard = document.getElementById('picker-card');
    const pickerScroll = document.getElementById('picker-scroll-container');
    pickerScroll.innerHTML = '';
    
    const showPicker = data.entries && data.entries.length > 0 && 
                       (currentCategory === '🖼️ Photo/Carousel' || currentCategory === '📱 Story');

    if (showPicker) {
        data.entries.forEach(item => {
            const row = document.createElement('div');
            row.className = 'picker-row';
            row.innerHTML = `
                <input type="checkbox" id="chk-item-${item.index}" class="checkbox-input" value="${item.index}" checked>
                <label for="chk-item-${item.index}">${item.title}</label>
            `;
            pickerScroll.appendChild(row);
        });
        pickerCard.classList.remove('hidden');
        log(`Loaded multiple items list checks (${data.entries.length} items).`);
    } else {
        pickerCard.classList.add('hidden');
    }
}

// Select All / Deselect All Toggle Checked properties
function toggleAllSlides(checked) {
    document.querySelectorAll('.picker-scroll .checkbox-input').forEach(chk => {
        chk.checked = checked;
    });
    log(`Checklists options swap state: ${checked ? 'Selected All' : 'Deselected All'}`);
}

// Render format options changes
function adjustFormatOptions() {
    const formatSel = document.getElementById('format-select').value;
    const qualitySel = document.getElementById('quality-select');
    
    // For audio MP3, lock to best audio
    if (formatSel === 'MP3') {
        qualitySel.value = 'Best Audio';
        qualitySel.disabled = true;
    } else {
        qualitySel.value = '720p';
        qualitySel.disabled = false;
    }
}

// Start Stream Download Triggers
function startDownload() {
    if (!analyzedData) return;

    const downloadBtn = document.getElementById('download-btn');
    const format = document.getElementById('format-select').value;
    const quality = document.getElementById('quality-select').value;
    const zipOption = document.getElementById('zip-select').value;

    const url = analyzedData.original_url;

    // Check if slider items selection download is needed
    if (currentCategory === '🖼️ Photo/Carousel' || currentCategory === '📱 Story') {
        const checkedIndexes = Array.from(document.querySelectorAll('.picker-scroll .checkbox-input'))
            .filter(chk => chk.checked)
            .map(chk => parseInt(chk.value));

        if (checkedIndexes.length === 0) {
            updateStatus('No slides selected.', 'error');
            log('Download error: checklist selection empty.');
            alert('Selection Error: Please select at least one media slide item to download.');
            return;
        }

        // If multiple list elements are checked and zip is enabled
        log(`Initiating dynamic carousel downloads. Selections indexes: ${checkedIndexes.join(', ')}`);
        
        // Find checked urls
        const selectedItems = analyzedData.entries.filter(item => checkedIndexes.includes(item.index));
        
        if (zipOption === 'zip') {
             // For simplicity in Vercel client-side: we pass URL coordinates
             // Vercel server downloads separate items and zips them for download stream
             triggerDirectRedirect(`/api/download?url=${encodeURIComponent(url)}&format=ZIP`);
        } else {
             // Download each separately by triggering downloads in loops
             selectedItems.forEach((item, index) => {
                 setTimeout(() => {
                     triggerDirectRedirect(`/api/download?url=${encodeURIComponent(item.url)}`);
                 }, index * 1000); // 1s gaps spacing to prevent browser link cancel downloads
             });
        }
        return;
    }

    // Default media stream proxy downloads
    let downloadUrl = `/api/download?url=${encodeURIComponent(url)}&format=${format}&quality=${quality}`;
    
    // For thumbnail redirects
    if (currentCategory === '🖼️ Cover Thumbnail' && analyzedData.thumbnail) {
         // Proxy cover image raw base64 or source thumbnail URL
         downloadUrl = `/api/download?url=${encodeURIComponent(analyzedData.original_url)}`;
    }

    log(`Starting download streaming path redirect: ${downloadUrl}`);
    
    // Animate progress spinner simulator
    const progressPanel = document.getElementById('progress-panel');
    const progressFill = document.getElementById('progress-bar-fill');
    const pctLbl = document.getElementById('metric-pct');
    
    progressPanel.classList.remove('hidden');
    downloadBtn.disabled = true;
    downloadBtn.innerText = 'Downloading...';
    
    // Simulate active download steps UI (since redirect yields browser download control)
    let progress = 0;
    progressFill.style.width = '0%';
    pctLbl.innerText = '0%';
    
    const interval = setInterval(() => {
        progress += 5;
        if (progress > 95) progress = 95;
        progressFill.style.width = `${progress}%`;
        pctLbl.innerText = `${progress}%`;
    }, 300);

    // Prompt browser download dialog redirect
    triggerDirectRedirect(downloadUrl);

    // Reset button controls after 8 seconds
    setTimeout(() => {
        clearInterval(interval);
        progressFill.style.width = '100%';
        pctLbl.innerText = '100%';
        downloadBtn.disabled = false;
        
        // categories title
        selectCategory(currentCategory, null);
        updateStatus('Download session completed!', 'online');
        log('Download process complete.');
    }, 8000);
}

// Redirect method for downloads triggers
function triggerDirectRedirect(url) {
    const a = document.createElement('a');
    a.href = url;
    a.target = '_blank';
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

// Change Theme colors (Light vs Dark) using CSS root tokens
function changeTheme() {
    const val = document.getElementById('theme-select').value;
    const root = document.documentElement;

    if (val === 'light') {
        root.style.setProperty('--bg-void', '#F3F4F6');
        root.style.setProperty('--card-bg', '#FFFFFF');
        root.style.setProperty('--border-color', '#E5E7EB');
        root.style.setProperty('--white-text', '#0D0D12');
        root.style.setProperty('--muted-text', '#6B7280');
        root.style.setProperty('--muted-bg', '#D1D5DB');
        log('Appearance configurations theme altered to Light.');
    } else {
        root.style.setProperty('--bg-void', '#0D0D12');
        root.style.setProperty('--card-bg', '#17171E');
        root.style.setProperty('--border-color', '#2C2C36');
        root.style.setProperty('--white-text', '#FFFFFF');
        root.style.setProperty('--muted-text', '#A0A0AA');
        root.style.setProperty('--muted-bg', '#3A3A3A');
        log('Appearance configurations theme reverted to Dark.');
    }
}
