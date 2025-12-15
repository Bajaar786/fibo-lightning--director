// Configuration - Update this URL after deploying your backend
const API_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000'
    : 'https://your-backend-name.onrender.com';  // TODO: Replace with your actual Render backend URL

// Check API health on load
async function checkHealth() {
    try {
        const response = await fetch(`${API_URL}/api/health`);
        const data = await response.json();
        
        if (!data.checks.ready) {
            showApiKeyWarning(data.checks);
        }
    } catch (error) {
        console.warn('Backend not reachable:', error);
    }
}

function showApiKeyWarning(checks) {
    const warning = document.createElement('div');
    warning.className = 'api-warning';
    warning.innerHTML = `
        <h3>⚠️ API Keys Needed</h3>
        <p>Set these in backend/.env:</p>
        <ul>
            ${!checks.fal_api ? '<li>FAL_API_KEY: Get from <a href="https://fal.ai/dashboard/keys" target="_blank">fal.ai</a></li>' : ''}
            ${!checks.gemini_api ? '<li>GEMINI_API_KEY: Get from <a href="https://aistudio.google.com/apikey" target="_blank">Google AI Studio</a></li>' : ''}
        </ul>
        <p>Then restart: <code>docker-compose restart backend</code></p>
    `;
    
    document.body.prepend(warning);
}



// Updated generate function
async function generateScene() {
    const loading = document.getElementById('loading');
    const resultImage = document.getElementById('result-image');
    const jsonOutput = document.getElementById('json-output');
    
    loading.style.display = 'block';
    resultImage.src = '';
    
    // Get values from UI - using new schema format
    const request = {
        prompt: document.getElementById('prompt').value,
        lighting_setup: [
            {
                type: "key",
                intensity: parseInt(document.getElementById('key-intensity').value) / 100.0,
                temperature: parseInt(document.getElementById('color-temp').value),
                direction_deg: parseInt(document.getElementById('light-angle').value),
                distance: 1.0,
                softness: 0.5
            }
        ],
        camera: {
            lens: document.getElementById('lens-select').value,
            f_stop: parseFloat(document.getElementById('aperture').value),
            focal_distance: 5.0,
            angle: "eye-level"
        },
        hdr_enabled: document.getElementById('hdr-toggle').checked,
        style: "cinematic",
        seed: Math.floor(Math.random() * 10000),
        output_size: "1024x1024"
    };
    
    try {
        const response = await fetch(`${API_URL}/api/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Generation failed');
        }
        
        const result = await response.json();
        
        if (result.success) {
            // Display image from FAL.ai URL
            resultImage.src = result.image_url;
            resultImage.onload = () => {
                loading.style.display = 'none';
            };
            
            // Display JSON
            jsonOutput.textContent = JSON.stringify(result.json_prompt, null, 2);
            
            // Show success
            showNotification('✨ Scene generated successfully!', 'success');
            
            // Log for demo
            console.log('Generated via API:', {
                request_id: result.request_id,
                hdr: result.metadata?.hdr,
                image_url: result.image_url,
                processing_time: result.processing_time_ms
            });
        } else {
            throw new Error('Generation failed');
        }
        
    } catch (error) {
        console.error('Error:', error);
        loading.style.display = 'none';
        
        // Show helpful error
        if (error.message.includes('FAL_API_KEY') || error.message.includes('key')) {
            showNotification('❌ API key missing. Check backend/.env file', 'error');
        } else {
            showNotification(`❌ ${error.message}`, 'error');
        }
    }
}

// Helper functions
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// UI Initialization
function initUI() {
    // Slider value updates
    const keyIntensity = document.getElementById('key-intensity');
    const keyValue = document.getElementById('key-value');
    keyIntensity.addEventListener('input', () => {
        keyValue.textContent = `${keyIntensity.value}%`;
    });

    const colorTemp = document.getElementById('color-temp');
    const tempValue = document.getElementById('temp-value');
    colorTemp.addEventListener('input', () => {
        const temp = parseInt(colorTemp.value);
        const tempType = temp < 3200 ? 'Tungsten' : temp < 5600 ? 'Neutral' : 'Daylight';
        tempValue.textContent = `${temp}K (${tempType})`;
    });

    const lightAngle = document.getElementById('light-angle');
    const angleValue = document.getElementById('angle-value');
    lightAngle.addEventListener('input', () => {
        angleValue.textContent = `${lightAngle.value}°`;
    });

    const aperture = document.getElementById('aperture');
    const apertureValue = document.getElementById('aperture-value');
    aperture.addEventListener('input', () => {
        apertureValue.textContent = aperture.value;
    });

    // Generate button
    document.getElementById('generate-btn').addEventListener('click', generateScene);

    // Preset buttons
    document.querySelectorAll('.preset').forEach(btn => {
        btn.addEventListener('click', () => {
            applyPreset(btn.dataset.preset);
        });
    });

    // Export JSON button
    document.getElementById('export-json').addEventListener('click', () => {
        const jsonText = document.getElementById('json-output').textContent;
        navigator.clipboard.writeText(jsonText);
        showNotification('📋 JSON copied to clipboard!', 'success');
    });
}

// Apply lighting presets
async function applyPreset(presetName) {
    try {
        const response = await fetch(`${API_URL}/api/presets/${presetName}`);
        if (response.ok) {
            const preset = await response.json();
            
            // Apply first light from preset to UI
            if (preset.lights && preset.lights.length > 0) {
                const light = preset.lights[0];
                document.getElementById('key-intensity').value = Math.round(light.intensity * 100);
                document.getElementById('color-temp').value = light.temperature;
                document.getElementById('light-angle').value = light.direction_deg;
                
                // Trigger UI updates
                document.getElementById('key-intensity').dispatchEvent(new Event('input'));
                document.getElementById('color-temp').dispatchEvent(new Event('input'));
                document.getElementById('light-angle').dispatchEvent(new Event('input'));
            }
            
            showNotification(`🎨 Applied ${presetName} preset`, 'success');
        }
    } catch (error) {
        console.error('Preset error:', error);
        showNotification('❌ Failed to load preset', 'error');
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    initUI();
    initRefine();
});

// Add notification styles to CSS
const style = document.createElement('style');
style.textContent = `
    .api-warning {
        background: #ff6b6b;
        color: white;
        padding: 20px;
        margin: 20px;
        border-radius: 10px;
        animation: pulse 2s infinite;
    }
    
    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        border-radius: 8px;
        color: white;
        z-index: 1000;
        animation: slideIn 0.3s ease;
    }
    
    .notification.success { background: #4ecdc4; }
    .notification.error { background: #ff6b6b; }
    .notification.info { background: #45b7d1; }
    
    @keyframes slideIn {
        from { transform: translateX(100%); }
        to { transform: translateX(0); }
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.8; }
    }
`;
document.head.appendChild(style);

// Add these functions to your existing script.js

// Initialize refine functionality
function initRefine() {
    const refineBtn = document.getElementById('refine-btn');
    const refineInput = document.getElementById('refine-instruction');
    
    if (!refineBtn || !refineInput) return;
    
    // Main refine button
    refineBtn.addEventListener('click', () => {
        const instruction = refineInput.value.trim();
        if (instruction) {
            applyRefinement(instruction);
        }
    });
    
    // Quick refine buttons
    document.querySelectorAll('.quick-refine').forEach(btn => {
        btn.addEventListener('click', () => {
            const instruction = btn.dataset.instruction;
            refineInput.value = instruction;
            applyRefinement(instruction);
        });
    });
    
    // Enter key in refine input
    refineInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const instruction = refineInput.value.trim();
            if (instruction) {
                applyRefinement(instruction);
            }
        }
    });
}

// Apply refinement
async function applyRefinement(instruction) {
    const currentJson = document.getElementById('json-output').textContent;
    const resultImage = document.getElementById('result-image');
    const refineStatus = document.getElementById('refine-status');
    
    if (!currentJson || currentJson.includes('waiting_for_generation')) {
        showRefineStatus('Please generate a scene first!', 'error');
        return;
    }
    
    try {
        showRefineStatus('Refining scene...', 'info');
        
        const request = {
            previous_json: JSON.parse(currentJson),
            instruction: instruction,
            hdr: document.getElementById('hdr-toggle').checked
        };
        
        const response = await fetch(`${API_URL}/api/refine`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });
        
        if (!response.ok) {
            throw new Error('Refinement failed');
        }
        
        const result = await response.json();
        
        if (result.success) {
            // Update image
            resultImage.src = result.image_url;
            
            // Update JSON display
            document.getElementById('json-output').textContent = 
                JSON.stringify(result.refined_json, null, 2);
            
            // Show success message
            const changes = Object.entries(result.changes || {})
                .map(([key, value]) => `${key}: ${value}`)
                .join(', ');
            
            showRefineStatus(
                `✅ Refined! Applied: "${result.instruction_applied}"<br>Changes: ${changes}`,
                'success'
            );
            
            // Add to history
            addToHistory(instruction, result.image_url);
            
            // Clear input
            document.getElementById('refine-instruction').value = '';
            
            console.log('Refinement applied:', result.changes);
        } else {
            throw new Error('Refinement failed');
        }
        
    } catch (error) {
        console.error('Refine error:', error);
        showRefineStatus(`❌ Error: ${error.message}`, 'error');
    }
}

// Show status messages
function showRefineStatus(message, type = 'info') {
    const statusEl = document.getElementById('refine-status');
    if (!statusEl) return;
    
    statusEl.innerHTML = message;
    statusEl.className = `refine-status ${type}`;
    
    // Auto-clear after 5 seconds
    setTimeout(() => {
        statusEl.innerHTML = '';
        statusEl.className = 'refine-status';
    }, 5000);
}

// Add to refinement history
function addToHistory(instruction, imageUrl) {
    // Create history section if it doesn't exist
    let historySection = document.querySelector('.refine-history');
    if (!historySection) {
        historySection = document.createElement('div');
        historySection.className = 'refine-history';
        historySection.innerHTML = '<h4>Refinement History</h4>';
        document.querySelector('.refine-section').appendChild(historySection);
    }
    
    // Add history item
    const historyItem = document.createElement('div');
    historyItem.className = 'history-item';
    historyItem.innerHTML = `
        <span class="history-instruction">"${instruction}"</span>
        <button class="small-btn" onclick="loadRefinement('${imageUrl}')">↻ Load</button>
    `;
    
    // Add to top
    historySection.appendChild(historyItem);
    
    // Limit history to 5 items
    const items = historySection.querySelectorAll('.history-item');
    if (items.length > 5) {
        items[0].remove();
    }
}

// Load a previous refinement
function loadRefinement(imageUrl) {
    const resultImage = document.getElementById('result-image');
    resultImage.src = imageUrl;
    showRefineStatus('Loaded previous refinement', 'info');
}

// Main initialization is handled above