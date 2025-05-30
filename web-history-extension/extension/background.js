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

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getPageContent') {
    // Handle request to get page content for manual indexing
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      if (!tabs || !tabs[0] || !tabs[0].id) {
        sendResponse({ error: 'No active tab found' });
        return;
      }
      
      const tab = tabs[0];
      
      // Skip excluded domains
      if (shouldExcludeUrl(tab.url)) {
        sendResponse({ error: 'URL is excluded from indexing' });
        return;
      }
      
      const contentData = await extractPageContent(tab.id);
      if (!contentData) {
        sendResponse({ error: 'Failed to extract content' });
        return;
      }
      
      sendResponse({ content: contentData });
    });
    return true; // Required for async sendResponse
  } else if (request.action === 'indexPage') {
    // Handle request to index page
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      if (!tabs || !tabs[0] || !tabs[0].id) {
        sendResponse({ error: 'No active tab found' });
        return;
      }
      
      const tab = tabs[0];
      
      // Skip excluded domains
      if (shouldExcludeUrl(tab.url)) {
        sendResponse({ error: 'URL is excluded from indexing' });
        return;
      }
      
      const contentData = await extractPageContent(tab.id);
      if (!contentData) {
        sendResponse({ error: 'Failed to extract content' });
        return;
      }
      
      await indexWebpage(tab.url, contentData.title, contentData.content);
      sendResponse({ success: true });
    });
    return true; // Required for async sendResponse
  }
});
