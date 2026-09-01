import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import { onMounted, onWillUnmount } from "@odoo/owl";

const SCHOOL_ROOT_MENU = "menu_school_root";
const COLLAPSED_STORAGE_KEY = "school_sidebar_collapsed";

function schoolMenuMatches(xmlid, name) {
    return !!xmlid && String(xmlid).split(".").pop() === name;
}

function schoolActionIdFromHash() {
    const match = window.location.hash.match(/action-(\d+)/);
    return match ? parseInt(match[1], 10) : null;
}

patch(WebClient.prototype, {
    setup() {
        super.setup();

        const applySidebarLayout = () => {
            const app = this.menuService.getCurrentApp();
            const isSchool = !!app && schoolMenuMatches(app.xmlid, SCHOOL_ROOT_MENU);
            document.body.classList.toggle("o_school_sidebar", isSchool);
            if (isSchool) {
                this._renderSchoolSidebar();
                this._syncSidebarActive();
            } else {
                this._schoolSidenavEl?.remove();
                this._schoolSidenavEl = null;
                this._schoolToggleEl?.remove();
                this._schoolToggleEl = null;
                document.body.classList.remove("o_school_sidebar_collapsed");
            }
        };
        const syncActive = () => this._syncSidebarActive();

        let sidebarObserver = null;
        let syncFrame = null;
        const syncScheduled = () => {
            if (syncFrame !== null) {
                return;
            }
            syncFrame = requestAnimationFrame(() => {
                syncFrame = null;
                if (document.body.classList.contains("o_school_sidebar")) {
                    this._syncSidebarActive();
                }
            });
        };

        onMounted(() => {
            applySidebarLayout();
            window.addEventListener("hashchange", syncActive);
            this.env.bus.addEventListener("MENUS:APP-CHANGED", applySidebarLayout);
            const header = document.querySelector("body.o_school_sidebar > header.o_navbar");
            sidebarObserver = new MutationObserver(syncScheduled);
            sidebarObserver.observe(header || document.body, { childList: true, subtree: true });
        });
        onWillUnmount(() => {
            window.removeEventListener("hashchange", syncActive);
            this.env.bus.removeEventListener("MENUS:APP-CHANGED", applySidebarLayout);
            sidebarObserver?.disconnect();
            if (syncFrame !== null) {
                cancelAnimationFrame(syncFrame);
                syncFrame = null;
            }
        });
    },

    _schoolTreeLeaves(node) {
        const leaves = [];
        if (node.actionID) {
            leaves.push(node);
        }
        for (const child of node.childrenTree || []) {
            leaves.push(...this._schoolTreeLeaves(child));
        }
        return leaves;
    },

    _renderSchoolSidebar() {
        const navbar = document.querySelector(
            "body.o_school_sidebar > header.o_navbar .o_main_navbar"
        );
        if (!navbar) {
            return;
        }
        if (this._schoolSidenavEl?.isConnected) {
            return;
        }
        this._schoolSidenavEl = null;

        const app = this.menuService.getCurrentApp();
        const tree = this.menuService.getMenuAsTree(app.id);
        const container = document.createElement("div");
        container.className = "o_school_sidenav";

        const addItem = (leaf) => {
            const item = document.createElement("a");
            item.className = "o_school_sidenav__item";
            item.dataset.menuXmlid = leaf.xmlid;
            item.dataset.actionId = leaf.actionID;
            item.href = "#";
            item.textContent = leaf.name;
            item.addEventListener("click", (ev) => {
                ev.preventDefault();
                const actionId = parseInt(leaf.actionID, 10);
                if (this.actionService?.doAction) {
                    this.actionService.doAction(actionId);
                } else {
                    window.location.hash = `/odoo/action-${actionId}`;
                }
            });
            container.appendChild(item);
        };

        const addGroup = (section) => {
            const label = document.createElement("div");
            label.className = "o_school_sidenav__group-label";
            label.dataset.menuXmlid = section.xmlid;
            label.textContent = section.name;
            container.appendChild(label);
            for (const leaf of this._schoolTreeLeaves(section)) {
                addItem(leaf);
            }
        };

        for (const section of tree.childrenTree || []) {
            if ((section.childrenTree || []).length > 0 && this._schoolTreeLeaves(section).length) {
                addGroup(section);
            } else if (section.actionID) {
                addItem(section);
            }
        }

        navbar.appendChild(container);
        this._schoolSidenavEl = container;
        this._createSidebarToggle();
        this._applySidebarCollapsedState();
    },

    _createSidebarToggle() {
        if (this._schoolToggleEl) {
            return;
        }
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "o_school_sidenav__toggle";
        btn.title = "Hide sidebar";
        btn.addEventListener("click", () => {
            const collapsed = !document.body.classList.contains("o_school_sidebar_collapsed");
            document.body.classList.toggle("o_school_sidebar_collapsed", collapsed);
            localStorage.setItem(COLLAPSED_STORAGE_KEY, collapsed ? "1" : "0");
            btn.title = collapsed ? "Show sidebar" : "Hide sidebar";
        });
        document.body.appendChild(btn);
        this._schoolToggleEl = btn;
    },

    _applySidebarCollapsedState() {
        const collapsed = localStorage.getItem(COLLAPSED_STORAGE_KEY) === "1";
        document.body.classList.toggle("o_school_sidebar_collapsed", collapsed);
        if (this._schoolToggleEl) {
            this._schoolToggleEl.title = collapsed ? "Show sidebar" : "Hide sidebar";
        }
    },

    _syncSidebarActive() {
        let activeId = null;
        const actionId = schoolActionIdFromHash();
        if (actionId) {
            const currentApp = this.menuService.getCurrentApp();
            const menu = this.menuService
                .getAll()
                .find((m) => m.actionID === actionId && m.appID === currentApp?.id);
            activeId = menu?.id ?? null;
        }
        for (const el of document.querySelectorAll(
            "body.o_school_sidebar .o_school_sidenav__item"
        )) {
            const isActive = activeId !== null && parseInt(el.dataset.actionId, 10) === activeId;
            el.classList.toggle("o_school_sidebar__active", isActive);
        }
    },
});