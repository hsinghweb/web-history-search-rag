// Listen for messages from the popup or background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'highlight') {
    highlightText(request.text);
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
function highlightText(textToHighlight) {
  // First clear any existing highlights
  clearHighlights();
  
  if (!textToHighlight || textToHighlight.length < 3) {
    return;
  }
  
  // Create a regex to find the text (case insensitive)
  const regex = new RegExp(escapeRegExp(textToHighlight), 'gi');
  
  // Find all text nodes in the document
  const textNodes = findTextNodes(document.body);
  
  // For each text node, check if it contains the text to highlight
  let foundMatch = false;
  
  textNodes.forEach(node => {
    const originalText = node.nodeValue;
    if (regex.test(originalText)) {
      foundMatch = true;
      
      // Replace the text with highlighted version
      const highlightedText = originalText.replace(regex, match => {
        return `<mark class="web-history-highlight">${match}</mark>`;
      });
      
      // Create a temporary element to hold the HTML
      const tempElement = document.createElement('span');
      tempElement.innerHTML = highlightedText;
      
      // Replace the original node with the new nodes
      const parent = node.parentNode;
      parent.replaceChild(tempElement, node);
      
      // Scroll to the first highlight
      if (foundMatch) {
        const firstHighlight = document.querySelector('.web-history-highlight');
        if (firstHighlight) {
          firstHighlight.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
          });
        }
      }
    }
  });
  
  return foundMatch;
}

// Clear all highlights
function clearHighlights() {
  const highlights = document.querySelectorAll('.web-history-highlight');
  highlights.forEach(highlight => {
    const parent = highlight.parentNode;
    const textNode = document.createTextNode(highlight.textContent);
    parent.replaceChild(textNode, highlight);
    parent.normalize(); // Merge adjacent text nodes
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
