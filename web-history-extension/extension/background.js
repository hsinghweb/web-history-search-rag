// Constants
const API_URL = 'http://localhost:8000';
const EXCLUDED_DOMAINS = [
  'mail.google.com',
  'web.whatsapp.com',
  'drive.google.com',
  'docs.google.com',
  'sheets.google.com',
  'slides.google.com',
  'calendar.google.com',
  'meet.google.com',
  'localhost',
  'chrome://'
];

// Check if a URL should be excluded from indexing
function shouldExcludeUrl(url) {
  try {
    const urlObj = new URL(url);
    return EXCLUDED_DOMAINS.some(domain => urlObj.hostname.includes(domain));
  } catch (e) {
    console.error('Invalid URL:', url);
    return true;
  }
}

// Extract text content from a webpage
async function extractPageContent(tabId) {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab || tab.id !== tabId) {
      console.log('Tab not found or not active');
      return null;
    }
    
    // Execute content script to extract text
    const results = await chrome.scripting.executeScript({
      target: { tabId },
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
    
    if (!results || results.length === 0) {
      console.log('No content extracted');
      return null;
    }
    
    return results[0].result;
  } catch (error) {
    console.error('Error extracting content:', error);
    return null;
  }
}

// Index a webpage
async function indexWebpage(url, title, content) {
  try {
    const response = await fetch(`${API_URL}/index`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        url,
        title,
        content,
        timestamp: new Date().toISOString()
      })
    });
    
    const data = await response.json();
    console.log('Indexing result:', data);
    
    // Update badge to show indexed status
    chrome.action.setBadgeText({ text: '✓' });
    chrome.action.setBadgeBackgroundColor({ color: '#4CAF50' });
    
    // Clear badge after 3 seconds
    setTimeout(() => {
      chrome.action.setBadgeText({ text: '' });
    }, 3000);
    
    return data;
  } catch (error) {
    console.error('Error indexing webpage:', error);
    
    // Show error badge
    chrome.action.setBadgeText({ text: '!' });
    chrome.action.setBadgeBackgroundColor({ color: '#F44336' });
    
    // Clear badge after 3 seconds
    setTimeout(() => {
      chrome.action.setBadgeText({ text: '' });
    }, 3000);
    
    return null;
  }
}

// Listen for tab updates
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  // Only process when the page is fully loaded
  if (changeInfo.status === 'complete' && tab.url) {
    // Skip excluded domains
    if (shouldExcludeUrl(tab.url)) {
      console.log('Skipping excluded URL:', tab.url);
      return;
    }
    
    console.log('Processing page:', tab.url);
    
    // Extract content
    const contentData = await extractPageContent(tabId);
    if (!contentData) {
      console.log('No content extracted, skipping indexing');
      return;
    }
    
    // Index the webpage
    await indexWebpage(tab.url, contentData.title, contentData.content);
  }
});

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'search') {
    searchWebpages(request.query)
      .then(results => sendResponse({ success: true, results }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Required for async sendResponse
  }
});

// Search for webpages
async function searchWebpages(query) {
  try {
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
    return data;
  } catch (error) {
    console.error('Error searching webpages:', error);
    throw error;
  }
}

// Get API stats
async function getApiStats() {
  try {
    const response = await fetch(`${API_URL}/stats`);
    if (!response.ok) {
      throw new Error(`Failed to get stats: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error getting API stats:', error);
    return null;
  }
}

// Check if API is available
async function checkApiAvailability() {
  try {
    const stats = await getApiStats();
    return !!stats;
  } catch (error) {
    console.error('API not available:', error);
    return false;
  }
}

// Initialize extension
async function initialize() {
  // Check if API is available
  const apiAvailable = await checkApiAvailability();
  
  if (apiAvailable) {
    console.log('API is available');
    chrome.action.setBadgeText({ text: 'ON' });
    chrome.action.setBadgeBackgroundColor({ color: '#4CAF50' });
    
    // Clear badge after 3 seconds
    setTimeout(() => {
      chrome.action.setBadgeText({ text: '' });
    }, 3000);
  } else {
    console.error('API is not available');
    chrome.action.setBadgeText({ text: 'OFF' });
    chrome.action.setBadgeBackgroundColor({ color: '#F44336' });
  }
}

// Run initialization
initialize();
