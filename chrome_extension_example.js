/**
 * Chrome Extension Example - Medicare Plan API Integration
 *
 * This demonstrates how to call the Medicare Plan API from a Chrome Extension
 * Uses fetch API which works in both background scripts and content scripts
 */

// Lambda Function URL (deployed)
const API_BASE_URL = 'https://thl4l5z7inky2smh6qte6ewfuy0gavym.lambda-url.us-east-1.on.aws';

/**
 * Get plans for a ZIP code in a specific state
 * @param {string} state - State abbreviation (ak, nh, vt, wy)
 * @param {string} zipCode - ZIP code
 * @param {boolean} includeDetails - Include full plan details (default: false for faster response)
 * @returns {Promise<Object>} API response
 */
async function getPlansForZip(state, zipCode, includeDetails = false) {
    const url = `${API_BASE_URL}/${state.toLowerCase()}/${zipCode}${includeDetails ? '' : '?details=0'}`;

    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
                // No CORS headers needed - Lambda Function URL handles CORS automatically
                // AWS adds Access-Control-Allow-Origin based on Function URL CORS config
            }
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error fetching plans:', error);
        throw error;
    }
}

/**
 * Get details for a specific plan
 * @param {string} state - State abbreviation
 * @param {string} planId - Contract Plan Segment ID
 * @returns {Promise<Object>} Plan details
 */
async function getPlanDetail(state, planId) {
    const url = `${API_BASE_URL}/${state.toLowerCase()}/plan/${planId}`;

    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error fetching plan details:', error);
        throw error;
    }
}

/**
 * List all available states
 * @returns {Promise<Object>} States list
 */
async function listStates() {
    const url = `${API_BASE_URL}/states`;

    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
    }
    return await response.json();
}

/**
 * List counties for a state
 * @param {string} state - State abbreviation
 * @returns {Promise<Object>} Counties list
 */
async function listCounties(state) {
    const url = `${API_BASE_URL}/${state.toLowerCase()}/counties`;

    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
    }
    return await response.json();
}

// =============================================================================
// Example Usage in Chrome Extension
// =============================================================================

/**
 * Example 1: Popup script - User enters ZIP code
 * This would be in popup.js or similar
 */
async function handleZipCodeLookup() {
    const zipInput = document.getElementById('zip-code');
    const stateSelect = document.getElementById('state');
    const resultsDiv = document.getElementById('results');

    const zipCode = zipInput.value.trim();
    const state = stateSelect.value;

    if (!zipCode || !state) {
        resultsDiv.innerHTML = '<p>Please enter a ZIP code and select a state</p>';
        return;
    }

    resultsDiv.innerHTML = '<p>Loading...</p>';

    try {
        // Get summary first (faster)
        const data = await getPlansForZip(state, zipCode, false);

        if (data.multi_county) {
            // Show county selection UI
            displayCountySelection(data);
        } else {
            // Single county - show plans directly
            const county = Object.keys(data.counties)[0];
            displayPlans(data.counties[county]);
        }
    } catch (error) {
        resultsDiv.innerHTML = `<p class="error">Error: ${error.message}</p>`;
    }
}

/**
 * Example 2: Display county selection for multi-county ZIPs
 */
function displayCountySelection(data) {
    const resultsDiv = document.getElementById('results');

    let html = `
        <h3>ZIP ${data.zip_code} spans multiple counties</h3>
        <p>Please select your county:</p>
        <ul class="county-list">
    `;

    for (const [county, countyData] of Object.entries(data.counties)) {
        const percentage = countyData.percentage ? ` (${countyData.percentage}% of ZIP)` : '';
        html += `
            <li>
                <button class="county-btn" data-county="${county}">
                    ${county} - ${countyData.plan_count} plans${percentage}
                </button>
            </li>
        `;
    }

    html += '</ul>';
    resultsDiv.innerHTML = html;

    // Add click handlers
    document.querySelectorAll('.county-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const county = e.target.dataset.county;
            const countyData = data.counties[county];

            // Load full details for selected county
            const fullData = await getPlansForZip(data.state_abbr.toLowerCase(), data.zip_code, true);
            displayPlans(fullData.counties[county]);
        });
    });
}

/**
 * Example 3: Display plans list
 */
function displayPlans(countyData) {
    const resultsDiv = document.getElementById('results');

    let html = `
        <h3>Found ${countyData.plan_count} plans</h3>
        <div class="plans-list">
    `;

    for (const plan of countyData.plans) {
        const summary = plan.summary;
        const details = plan.details;

        html += `
            <div class="plan-card">
                <h4>${summary.plan_name}</h4>
                <p><strong>Organization:</strong> ${summary.organization}</p>
                <p><strong>Type:</strong> ${summary.plan_type}</p>
                ${summary.part_c_premium ? `<p><strong>Part C Premium:</strong> ${summary.part_c_premium}</p>` : ''}
                ${summary.overall_star_rating !== 'Not Applicable' ? `<p><strong>Rating:</strong> ${summary.overall_star_rating} stars</p>` : ''}

                ${plan.has_scraped_details && details ? `
                    <div class="plan-details">
                        <p><strong>Premium:</strong> ${details.premiums['Total monthly premium'] || 'N/A'}</p>
                        <p><strong>Deductible:</strong> ${details.deductibles['Drug deductible'] || 'N/A'}</p>
                        ${details.contact_info['Plan address'] ? `<p><strong>Address:</strong><br>${details.contact_info['Plan address'].replace(/\n/g, '<br>')}</p>` : ''}
                    </div>
                ` : ''}

                <button class="view-more-btn" data-plan-id="${summary.contract_plan_segment_id}">
                    View Full Details
                </button>
            </div>
        `;
    }

    html += '</div>';
    resultsDiv.innerHTML = html;
}

/**
 * Example 4: Background script - Cache API data
 * This would be in background.js or service_worker.js
 */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getPlans') {
        getPlansForZip(request.state, request.zipCode, request.includeDetails)
            .then(data => sendResponse({ success: true, data }))
            .catch(error => sendResponse({ success: false, error: error.message }));
        return true; // Required for async sendResponse
    }

    if (request.action === 'getPlanDetail') {
        getPlanDetail(request.state, request.planId)
            .then(data => sendResponse({ success: true, data }))
            .catch(error => sendResponse({ success: false, error: error.message }));
        return true;
    }
});

/**
 * Example 5: Content script - Detect ZIP codes on page
 * This would be in content_script.js
 */
function highlightZipCodesOnPage() {
    // Simple ZIP code regex
    const zipRegex = /\b\d{5}(?:-\d{4})?\b/g;

    // Find all text nodes
    const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_TEXT,
        null,
        false
    );

    const textNodes = [];
    let node;
    while (node = walker.nextNode()) {
        if (zipRegex.test(node.textContent)) {
            textNodes.push(node);
        }
    }

    // Add tooltips to ZIP codes
    textNodes.forEach(node => {
        const parent = node.parentElement;
        const text = node.textContent;
        const match = text.match(zipRegex);

        if (match) {
            const zipCode = match[0];
            parent.setAttribute('data-medicare-zip', zipCode);
            parent.style.cursor = 'pointer';
            parent.title = `Click to find Medicare plans for ${zipCode}`;

            parent.addEventListener('click', async () => {
                // Determine state (you'd need logic here based on page context or asking user)
                const state = 'nh'; // Example
                const data = await getPlansForZip(state, zipCode, false);
                showTooltip(parent, data);
            });
        }
    });
}

// =============================================================================
// Manifest V3 Service Worker Example
// =============================================================================

/**
 * Example manifest.json for Chrome Extension
 * {
 *   "manifest_version": 3,
 *   "name": "Medicare Plan Finder",
 *   "version": "1.0",
 *   "permissions": [],
 *   "host_permissions": [
 *     "https://*.amazonaws.com/*",
 *     "https://*.lambda-url.us-east-1.on.aws/*"
 *   ],
 *   "background": {
 *     "service_worker": "background.js"
 *   },
 *   "action": {
 *     "default_popup": "popup.html"
 *   }
 * }
 */

// Export for use in other modules (if using modules in extension)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getPlansForZip,
        getPlanDetail,
        listStates,
        listCounties
    };
}
