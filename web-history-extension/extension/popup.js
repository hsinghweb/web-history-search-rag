// Constants
const API_URL = 'http://localhost:8000';

// DOM elements
const searchInput = document.getElementById('search-input');
const searchButton = document.getElementById('search-button');
const resultsContainer = document.getElementById('results-container');
const statusText = document.getElementById('status-text');
const statusIndicator = document.getElementById('status-indicator');
const indexedCount = document.getElementById('indexed-count');
const indexCurrentButton = document.getElementById('index-current-button');
const settingsButton = document.getElementById('settings-button');

// Initialize popup
document.addEventListener('DOMContentLoaded', async () => {
  // Focus search input
  searchInput.focus();
  
  // Check API status
  await checkApiStatus();
  
  // Load stats
  await loadStats();
  
  // Set up event listeners
  setupEventListeners();
});

// Set up event listeners
function setupEventListeners() {
  // Search button click
  searchButton.addEventListener('click', handleSearch);
  
  // Search input enter key
  searchInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      handleSearch();
    }
  });
  
  // Index current page button
  indexCurrentButton.addEventListener('click', indexCurrentPage);
  
  // Settings button
  settingsButton.addEventListener('click', openSettings);
}

// Check API status
async function checkApiStatus() {
  try {
    const response = await fetch(`${API_URL}/stats`);
    if (response.ok) {
      statusText.textContent = 'API Online';
      statusIndicator.classList.add('online');
      return true;
    } else {
      throw new Error('API returned error');
    }
  } catch (error) {
    statusText.textContent = 'API Offline';
    statusIndicator.classList.add('offline');
    console.error('API status check failed:', error);
    return false;
  }
}

// Load stats
async function loadStats() {
  try {
    const response = await fetch(`${API_URL}/stats`);
    if (response.ok) {
      const stats = await response.json();
      indexedCount.textContent = stats.indexed_urls || 0;
    }
  } catch (error) {
    console.error('Failed to load stats:', error);
  }
}

// Handle search
async function handleSearch() {
  const query = searchInput.value.trim();
  if (!query) {
    return;
  }
  
  // Show loading state
  showLoading();
  
  try {
    // Send search request
    const response = await fetch(`${API_URL}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        query,
        top_k: 5
      })
    });
    
    if (!response.ok) {
      throw new Error(`Search failed: ${response.statusText}`);
    }
    
    const data = await response.json();
    displayResults(data);
  } catch (error) {
    showError(error.message);
    console.error('Search error:', error);
  }
}

// Display search results
function displayResults(data) {
  // Clear results container
  resultsContainer.innerHTML = '';
  
  if (!data.results || data.results.length === 0) {
    resultsContainer.innerHTML = '<div class="no-results">No results found</div>';
    return;
  }
  
  // Create result items
  data.results.forEach(result => {
    const resultItem = document.createElement('div');
    resultItem.className = 'result-item';
    resultItem.dataset.url = result.url;
    resultItem.dataset.snippet = result.content_snippet;
    
    resultItem.innerHTML = `
      <div class="result-title">${result.title}</div>
      <div class="result-url">${result.url}</div>
      <div class="result-snippet">${highlightQuery(result.content_snippet, data.query)}</div>
    `;
    
    // Add click event to open the page and highlight text
    resultItem.addEventListener('click', () => {
      openPageAndHighlight(result.url, result.content_snippet, data.query);
    });
    
    resultsContainer.appendChild(resultItem);
  });
}

// Highlight query terms in snippet
function highlightQuery(snippet, query) {
  const words = query.split(/\s+/).filter(word => word.length > 2);
  let highlightedSnippet = snippet;
  
  words.forEach(word => {
    const regex = new RegExp(escapeRegExp(word), 'gi');
    highlightedSnippet = highlightedSnippet.replace(regex, match => {
      return `<span style="background-color: #ffeb3b; font-weight: bold;">${match}</span>`;
    });
  });
  
  return highlightedSnippet;
}

// Escape special characters in regex
function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Show loading state
function showLoading() {
  resultsContainer.innerHTML = `
    <div class="loading">
      <div class="spinner"></div>
    </div>
  `;
}

// Show error message
function showError(message) {
  resultsContainer.innerHTML = `
    <div class="no-results">
      Error: ${message}
    </div>
  `;
}

// Index current page
async function indexCurrentPage() {
  try {
    // Get current tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab) {
      throw new Error('No active tab found');
    }
    
    // Show indexing status
    indexCurrentButton.textContent = 'Indexing...';
    indexCurrentButton.disabled = true;

    // Inject content script only when needed
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ['content.js']
    });

    // Inject CSS for highlighting
    await chrome.scripting.insertCSS({
      target: { tabId: tab.id },
      files: ['highlight.css']
    });
    
    // Get page content
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      function: () => {
        // Get page title
        const title = document.title;
        
        // Get text content
        const bodyText = document.body.innerText;
        
        // Get meta description
        const metaDescription = document.querySelector('meta[name="description"]')?.content || '';
        
        // Combine all text
        const content = `${title}\n${metaDescription}\n${bodyText}`;
        
        return {
          title,
          content
        };
      }
    });

    if (!results || !results[0].result) {
      throw new Error('Failed to get page content');
    }

    const contentData = results[0].result;
    
    // Send content to API
    const apiResponse = await fetch(`${API_URL}/index`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        url: tab.url,
        title: contentData.title,
        content: contentData.content,
        timestamp: new Date().toISOString()
      })
    });
    
    if (!apiResponse.ok) {
      throw new Error(`Indexing failed: ${apiResponse.statusText}`);
    }
    
    // Update button state
    indexCurrentButton.textContent = 'Indexed!';
    setTimeout(() => {
      indexCurrentButton.textContent = 'Index Current Page';
      indexCurrentButton.disabled = false;
    }, 2000);
    
    // Refresh stats
    await loadStats();
  } catch (error) {
    indexCurrentButton.textContent = 'Failed';
    setTimeout(() => {
      indexCurrentButton.textContent = 'Index Current Page';
      indexCurrentButton.disabled = false;
    }, 2000);
    console.error('Error indexing current page:', error);
  }
}

// Open settings
function openSettings() {
  chrome.runtime.openOptionsPage();
}

// Open page and highlight text with robust retry
async function openPageAndHighlight(url, chunkText, searchQuery) {
  try {
    const tab = await chrome.tabs.create({ url });
    // Wait for page to load
    chrome.tabs.onUpdated.addListener(function listener(tabId, changeInfo) {
      if (tabId === tab.id && changeInfo.status === 'complete') {
        chrome.tabs.onUpdated.removeListener(listener);
        // Inject content script and CSS
        chrome.scripting.executeScript({
          target: { tabId: tab.id },
          files: ['content.js']
        }).then(() => {
          chrome.scripting.insertCSS({
            target: { tabId: tab.id },
            files: ['highlight.css']
          }).then(() => {
            // Retry sending the message until acknowledged
            let tries = 0;
            function trySend() {
              chrome.tabs.sendMessage(tab.id, {
                action: 'highlight-chunk',
                chunkText: chunkText,
                searchText: searchQuery
              }, (response) => {
                if (!response && tries < 5) {
                  tries++;
                  setTimeout(trySend, 500);
                }
              });
            }
            setTimeout(trySend, 1000); // Initial delay
          });
        });
      }
    });
  } catch (error) {
    console.error('Error opening page:', error);
  }
}
