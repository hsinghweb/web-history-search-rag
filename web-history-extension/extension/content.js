// Listen for messages from the popup or background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'highlight') {
    highlightText(request.searchText, request.matchText, request.chunkId);
    sendResponse({ success: true });
  } else if (request.action === 'highlight-chunk') {
    // Try to highlight by chunkId if possible, else by chunkText
    highlightChunk(request.chunkText, request.searchText, request.chunkId);
    highlightQueryTextEverywhere(request.searchText);
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

function normalizeText(text) {
  return text.replace(/\s+/g, ' ').replace(/[\r\n]+/g, ' ').trim();
}

function fuzzyIncludes(source, target) {
  // Returns true if at least 80% of target is found in source (normalized, case-insensitive)
  const normSource = normalizeText(source).toLowerCase();
  const normTarget = normalizeText(target).toLowerCase();
  if (normTarget.length < 10) return false;
  return normSource.includes(normTarget.slice(0, Math.max(20, Math.floor(normTarget.length * 0.8))));
}

function highlightChunk(chunkText, searchText, chunkId) {
  clearHighlights();
  if (!chunkText || chunkText.length < 3) return;
  // Try to reconstruct chunks and match by chunkId
  if (chunkId !== undefined && chunkId !== null) {
    const allText = document.body.innerText;
    const chunks = chunkTextify(allText, 500); // Use same chunk size as backend
    if (chunks[chunkId]) {
      highlightTextEverywhere(chunks[chunkId], 'web-history-chunk-highlight');
      // Also highlight search terms inside the chunk
      highlightTermsInChunk(document.body, searchText);
      // Scroll to first chunk highlight
      const first = document.querySelector('.web-history-chunk-highlight');
      if (first) first.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
  }
  // Fallback: fuzzy match chunkText as before
  const textNodes = findTextNodes(document.body);
  let found = false;
  const normChunk = normalizeText(chunkText);
  for (const node of textNodes) {
    const nodeNorm = normalizeText(node.nodeValue);
    if (fuzzyIncludes(nodeNorm, normChunk)) {
      const regex = new RegExp(escapeRegExp(chunkText.slice(0, 40)), 'i');
      const highlightedHTML = node.nodeValue.replace(regex, match => `<mark class="web-history-chunk-highlight">${match}</mark>`);
      const temp = document.createElement('span');
      temp.innerHTML = highlightedHTML;
      node.parentNode.replaceChild(temp, node);
      highlightTermsInChunk(temp, searchText);
      temp.scrollIntoView({ behavior: 'smooth', block: 'center' });
      found = true;
      break;
    }
  }
  if (!found) {
    highlightText(searchText, '');
  }
}

function chunkTextify(text, chunkSize) {
  // Simple chunking by sentence and length, similar to backend
  const sentences = text.split(/(?<=[.!?])\s+/);
  let chunks = [];
  let current = '';
  for (const sentence of sentences) {
    if ((current + sentence).length > chunkSize && current.length > 0) {
      chunks.push(current);
      current = '';
    }
    current += sentence + ' ';
  }
  if (current.length > 0) {
    chunks.push(current.trim());
  }
  return chunks;
}

function highlightTextEverywhere(target, cssClass) {
  if (!target || target.length < 3) return;
  const textNodes = findTextNodes(document.body);
  for (const node of textNodes) {
    const regex = new RegExp(escapeRegExp(target.slice(0, 40)), 'i');
    if (regex.test(node.nodeValue)) {
      const highlightedHTML = node.nodeValue.replace(regex, match => `<mark class="${cssClass}">${match}</mark>`);
      const temp = document.createElement('span');
      temp.innerHTML = highlightedHTML;
      node.parentNode.replaceChild(temp, node);
    }
  }
}

function highlightTermsInChunk(chunkElem, searchText) {
  if (!searchText) return;
  const words = searchText.split(/\s+/).filter(w => w.length > 2);
  for (const word of words) {
    const regex = new RegExp(escapeRegExp(word), 'gi');
    chunkElem.innerHTML = chunkElem.innerHTML.replace(regex, m => `<mark class="web-history-term-highlight">${m}</mark>`);
  }
}

function highlightQueryTextEverywhere(queryText) {
  if (!queryText || queryText.length < 2) return;
  clearHighlights();
  const textNodes = findTextNodes(document.body);
  let firstMark = null;
  for (const node of textNodes) {
    const regex = new RegExp(escapeRegExp(queryText), 'gi');
    if (regex.test(node.nodeValue)) {
      const highlightedHTML = node.nodeValue.replace(regex, match => `<mark class="web-history-query-highlight">${match}</mark>`);
      const temp = document.createElement('span');
      temp.innerHTML = highlightedHTML;
      node.parentNode.replaceChild(temp, node);
      if (!firstMark) {
        firstMark = temp.querySelector('mark.web-history-query-highlight');
      }
    }
  }
  if (firstMark) {
    firstMark.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
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
