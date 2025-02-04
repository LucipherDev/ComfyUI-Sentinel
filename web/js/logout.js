import { $el } from "/scripts/ui.js";

async function setupLogout() {
  try {
    await new Promise((resolve) => {
      const interval = setInterval(() => {
        if (document.querySelector(".side-tool-bar-end")) {
          clearInterval(interval);
          resolve();
        }
      }, 100);
    });

    function logoutAction() {
      try {
        localStorage.clear();
        sessionStorage.clear();
        document.cookie.split(";").forEach((cookie) => {
          const cookieName = cookie.split("=")[0].trim();
          document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/`;
        });

        window.location.href = "/logout";
      } catch (error) {
        console.error("Error during logout process:", error);
      }
    }

    $el(
      "button",
      {
        className:
          "p-button p-component p-button-icon-only p-button-text comfy-settings-btn side-bar-button p-button-secondary sentinel-logout",
        type: "button",
        id: "logout-button",
        ariaLabel: "Logout",
        dataset: {
          pcName: "button",
          pDisabled: false,
          pcSection: "root",
          pdTooltip: false,
          "v-6ab4daa6": "",
          "v-33cac83a": "",
        },
        parent: document.querySelector(".side-tool-bar-end"),
        onclick: logoutAction,
      },
      [
        $el("li", {
          className: "pi pi-sign-out side-bar-button-icon",
          dataset: {
            "v-6ab4daa6": "",
          },
        }),
      ]
    );

    $el(
      "button",
      {
        textContent: "Logout",
        id: "logout-menu-button",
        parent: document.querySelector(".comfy-menu"),
        onclick: logoutAction,
      },
      [
        $el("li", {
          className: "pi pi-sign-out logout-icon",
        }),
      ]
    );

  } catch (error) {
    console.error("Error setting up Logout button:", error);
  }
}

let isSettingUp = false;

setInterval(async () => {
  if (document.getElementById("logout-button") === null && !isSettingUp) {
    isSettingUp = true;
    await setupLogout();
    isSettingUp = false;
  }
}, 500);