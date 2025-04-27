// Listen for messages from the popup or background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'highlight') {
    highlightText(request.searchText, request.matchText, request.chunkId);
    sendResponse({ success: true });
  } else if (request.action === 'clearHighlights') {
    clearHighlights();
    sendResponse({ success: true });
  } else if (request.action === 'getPageContent') {
    const content = extractPageContent();
    sendResponse({ content });
  }
  return true;
});

// Extract page content
function extractPageContent() {
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

// Highlight text on the page
function highlightText(searchText, matchText, chunkId) {
  // First clear any existing highlights
  clearHighlights();
  
  // Create a regex pattern that matches both search text and match text
  const searchPattern = new RegExp(escapeRegExp(searchText), 'gi');
  const matchPattern = new RegExp(escapeRegExp(matchText), 'gi');
  
  // Find all text nodes in the document
  const textNodes = findTextNodes(document.body);
  
  // Track the best match for scrolling
  let bestMatch = null;
  let bestMatchScore = 0;
  
  // First try to highlight the exact match text
  textNodes.forEach(node => {
    const originalText = node.nodeValue;
    if (matchPattern.test(originalText)) {
      const highlightedText = originalText.replace(matchPattern, match => {
        return `<mark class="web-history-highlight match-highlight" data-chunk-id="${chunkId}">${match}</mark>`;
      });
      
      const tempElement = document.createElement('span');
      tempElement.innerHTML = highlightedText;
      node.parentNode.replaceChild(tempElement, node);
      
      const highlight = tempElement.querySelector('.match-highlight');
      if (highlight) {
        const matchScore = calculateMatchScore(originalText, matchText);
        if (matchScore > bestMatchScore) {
          bestMatchScore = matchScore;
          bestMatch = highlight;
        }
      }
    }
  });
  
  // Then highlight search terms in a different color
  textNodes.forEach(node => {
    const originalText = node.nodeValue;
    if (searchPattern.test(originalText)) {
      const highlightedText = originalText.replace(searchPattern, match => {
        return `<mark class="web-history-highlight search-highlight">${match}</mark>`;
      });
      
      const tempElement = document.createElement('span');
      tempElement.innerHTML = highlightedText;
      node.parentNode.replaceChild(tempElement, node);
    }
  });

  // Scroll to the best match if found
  if (bestMatch) {
    bestMatch.scrollIntoView({
      behavior: 'smooth',
      block: 'center'
    });
    
    // Add pulsing animation
    bestMatch.classList.add('highlight-pulse');
    
    // Remove pulsing after animation completes
    setTimeout(() => {
      bestMatch.classList.remove('highlight-pulse');
    }, 2000);
  }
}

// Calculate match score between text and search/match text
function calculateMatchScore(text, targetText) {
  const textWords = text.toLowerCase().split(/\s+/);
  const targetWords = targetText.toLowerCase().split(/\s+/);
  
  let matchCount = 0;
  targetWords.forEach(word => {
    if (textWords.includes(word)) {
      matchCount++;
    }
  });
  
  return matchCount / targetWords.length;
}

// Clear all highlights
function clearHighlights() {
  const highlights = document.querySelectorAll('.web-history-highlight');
  highlights.forEach(highlight => {
    const parent = highlight.parentNode;
    const textNode = document.createTextNode(highlight.textContent);
    parent.replaceChild(textNode, highlight);
    parent.normalize();
  });
}

// Find all text nodes in an element
function findTextNodes(element) {
  const textNodes = [];
  const walker = document.createTreeWalker(
    element,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode: function(node) {
        // Skip script and style elements
        if (node.parentNode.tagName === 'SCRIPT' || 
            node.parentNode.tagName === 'STYLE' ||
            node.parentNode.tagName === 'NOSCRIPT') {
          return NodeFilter.FILTER_REJECT;
        }
        // Skip empty text nodes
        if (node.nodeValue.trim() === '') {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      }
    }
  );
  
  let node;
  while (node = walker.nextNode()) {
    textNodes.push(node);
  }
  
  return textNodes;
}

// Escape special characters in regex
function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
