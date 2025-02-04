import { $el } from "/scripts/ui.js";

$el("style", {
  textContent: `
  .sentinel-logout {
    color: var(--p-red-600) !important;
  }
  
  .sentinel-logout:hover {
    background: var(--p-red-600) !important;
    color: var(--p-red-300) !important;
  }

  #logout-menu-button {
    background-color: var(--p-red-600) !important;
  }

  #logout-menu-button {
    background-color: var(--p-red-500) !important;
  }

  #logout-menu-button .logout-icon {
    margin: 8px 0 8px 10px;
    font-size: 15px;
  }
  `,
  parent: document.head,
});
