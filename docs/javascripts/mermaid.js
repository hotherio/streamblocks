/**
 * Mermaid configuration for rendering diagrams
 */
window.mermaidConfig = {
  startOnLoad: false,
  theme: document.body.getAttribute("data-md-color-scheme") === "slate" ? "dark" : "default",
  themeVariables: {
    fontSize: "16px"
  }
};

// Initialize Mermaid when the page loads
document$.subscribe(function() {
  // Wait for Mermaid library to be available
  if (typeof mermaid !== 'undefined') {
    mermaid.initialize(window.mermaidConfig);

    // Find all Mermaid code blocks (pre.mermaid) and convert them to divs
    document.querySelectorAll("pre.mermaid").forEach(function(pre) {
      var code = pre.querySelector("code");
      if (code) {
        var div = document.createElement("div");
        div.className = "mermaid";
        div.textContent = code.textContent;
        pre.parentElement.replaceChild(div, pre);
      }
    });

    // Now render all mermaid divs
    document.querySelectorAll("div.mermaid").forEach(function(element) {
      // Only render if not already rendered
      if (!element.hasAttribute("data-processed")) {
        try {
          mermaid.init(undefined, element);
        } catch (e) {
          console.error("Mermaid rendering error:", e);
        }
      }
    });
  }
});

// Update theme when color scheme changes
var observer = new MutationObserver(function(mutations) {
  mutations.forEach(function(mutation) {
    if (mutation.attributeName === "data-md-color-scheme") {
      var scheme = document.body.getAttribute("data-md-color-scheme");
      window.mermaidConfig.theme = scheme === "slate" ? "dark" : "default";
      if (typeof mermaid !== 'undefined') {
        mermaid.initialize(window.mermaidConfig);
      }
    }
  });
});

observer.observe(document.body, {
  attributes: true,
  attributeFilter: ["data-md-color-scheme"]
});
