// Selects a model by pressing on card
// targetPrefix routes selection to a different hidden textbox set (e.g. 'local'
// → #local_model_select), so the Local Models browser can reuse this function
// without touching the Browser tab's wiring. Empty prefix = Browser (default).
function select_model(model_name, event, bool = false, content_type = null, sendToBrowser = false, targetPrefix = '') {
    if (event) {
        var className = event.target.className;
        if (className.includes('custom-checkbox') || className.includes('model-checkbox')) {
            return;
        }
    }

    let output;
    if (sendToBrowser) {
        output = gradioApp().querySelector('#send_to_browser textarea');
    } else if (targetPrefix) {
        output = gradioApp().querySelector(`#${targetPrefix}_model_select textarea`);
    } else {
        output = bool ? gradioApp().querySelector('#model_sent textarea') : gradioApp().querySelector('#model_select textarea');
    }

    if (output && model_name) {
        const randomNumber = Math.floor(Math.random() * 1000);
        const paddedNumber = String(randomNumber).padStart(3, '0');
        output.value = model_name + '.' + paddedNumber;
        updateInput(output);
    }

    if (content_type) {
        const outputType = gradioApp().querySelector('#type_sent textarea');
        if (outputType) {
            const randomNumber = Math.floor(Math.random() * 1000);
            const paddedNumber = String(randomNumber).padStart(3, '0');
            outputType.value = content_type + '.' + paddedNumber;
            updateInput(outputType);
        }
    }
}

// Clicks the first item in the browser cards list
function clickFirstFigureInColumn() {
    setTimeout(() => {
        const columnDiv = document.querySelector('.column.civmodellist');
        if (columnDiv) {
            const firstFigure = columnDiv.querySelector('figure');
            if (firstFigure) {
                firstFigure.click();
            }
        }
    }, 500);
}

// === ANXETY EDITs ===
// Changes the card size
function updateCardSize(width, height) {
    var styleSheet = document.styleSheets[0];
    var dimensionsKeyframes = `width: ${width}em !important; height: ${height}em !important;`;

    var fontSize = (width / 12) * 100;
    var textKeyframes = `font-size: ${fontSize}% !important;`;

    addOrUpdateRule(styleSheet, '.civmodelcard img', dimensionsKeyframes);
    addOrUpdateRule(styleSheet, '.civmodelcard .video-bg', dimensionsKeyframes);
    addOrUpdateRule(styleSheet, '.civmodelcard figcaption', textKeyframes);

    // Hide badges when tile size is less than 11
    var badgeDisplay = width < 11 ? 'none !important' : 'flex !important';
    addOrUpdateRule(styleSheet, '.model-type-badge', `display: ${badgeDisplay}`);
    addOrUpdateRule(styleSheet, '.nsfw-badge', `display: ${badgeDisplay}`);

    // Hide outdated-card delete button when tile size is less than 11 (same threshold as badges)
    var outdatedDeleteDisplay = width < 11 ? 'none !important' : 'flex !important';
    addOrUpdateRule(styleSheet, '.outdated-card-actions .delete-model-btn', `display: ${outdatedDeleteDisplay}`);
}

// Updates site with css insertions
function addOrUpdateRule(styleSheet, selector, newRules) {
    for (let i = 0; i < styleSheet.cssRules.length; i++) {
        let rule = styleSheet.cssRules[i];
        if (rule.selectorText === selector) {
            rule.style.cssText = newRules;
            return;
        }
    }
    styleSheet.insertRule(`${selector} { ${newRules} }`, styleSheet.cssRules.length);
}

// === ANXETY EDITs ===
// Updates card border
const cardSyncRetryState = {};
const pendingCardUpdates = new Set();

function applyPendingCardUpdates() {
    if (pendingCardUpdates.size === 0) return;
    const toApply = Array.from(pendingCardUpdates);
    pendingCardUpdates.clear();
    toApply.forEach((modelNameWithSuffix) => {
        updateCard(modelNameWithSuffix, false);
    });
}

// Watch for card containers appearing in the DOM (e.g. when user switches back to Browser/Update tab)
(function initCardUpdateObserver() {
    const observer = new MutationObserver((mutations) => {
        let foundContainer = false;
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    if (
                        node.matches && (node.matches('.civmodellist') || node.matches('.civmodelcards'))
                    ) {
                        foundContainer = true;
                    } else if (node.querySelector) {
                        if (
                            node.querySelector('.civmodellist') ||
                            node.querySelector('.civmodelcards')
                        ) {
                            foundContainer = true;
                        }
                    }
                }
            }
        }
        if (foundContainer) {
            // Re-apply DOM filters after Gradio finishes injecting the new HTML
            setTimeout(reapplyFilters, 250);

            if (pendingCardUpdates.size > 0) {
                console.log('[updateCard] container appeared — applying', pendingCardUpdates.size, 'pending update(s)');
                // Small delay to let Gradio finish rendering cards inside the container
                setTimeout(applyPendingCardUpdates, 200);
            }
        }
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
})();

// Polling fallback: Gradio 4.x often injects cards via innerHTML which doesn't reliably
// trigger childList mutations for individual cards. We poll every 600ms to check if
// any visible container now has cards, and apply pending updates if so.
(function initCardUpdatePoller() {
    setInterval(() => {
        if (pendingCardUpdates.size === 0) return;

        const containers = [
            ...document.querySelectorAll('.civmodellist'),
            ...document.querySelectorAll('.civmodelcards')
        ];

        if (containers.length === 0) {
            console.log('[updateCard] poller: no containers in DOM');
            return;
        }

        // If any container has cards, apply pending updates directly.
        const hasCards = containers.some((container) => {
            return container.querySelectorAll('.civmodelcard').length > 0;
        });

        if (hasCards) {
            console.log('[updateCard] poller: cards detected — applying', pendingCardUpdates.size, 'pending update(s)');
            applyPendingCardUpdates();
            reapplyFilters();
        } else {
            // Containers exist but have no cards (Gradio cleared them on tab switch).
            // Force a refresh to reload cards with updated status.
            console.log('[updateCard] poller: containers empty — forcing refresh');
            pendingCardUpdates.clear();
            pressRefresh();
        }
    }, 600);
})();

function updateCard(modelNameWithSuffix, allowRefresh = true) {
    if (!modelNameWithSuffix || typeof modelNameWithSuffix !== 'string') {
        return;
    }

    const lastDotIndex = modelNameWithSuffix.lastIndexOf('.');
    if (lastDotIndex <= 0) {
        return;
    }

    const modelName = modelNameWithSuffix.slice(0, lastDotIndex);
    const suffix = modelNameWithSuffix.slice(lastDotIndex + 1);

    let additionalClassName = '';
    switch (suffix) {
        case 'None':
            additionalClassName = '';
            break;
        case 'Old':
            additionalClassName = 'civmodelcardoutdated';
            break;
        case 'New':
            additionalClassName = 'civmodelcardinstalled';
            break;
        default:
            return;
    }

    // Extract modelId from anywhere in the string (e.g. "Name (12345).New")
    // instead of requiring it at the end — the suffix (.New/.Old/.None) comes after.
    const modelIdMatch = modelNameWithSuffix.match(/\((-?\d+)\)/);
    const modelId = modelIdMatch ? modelIdMatch[1] : null;
    const statusClasses = ['civmodelcardinstalled', 'civmodelcardoutdated', 'civmodelcardcrossfamily'];

    // Search ALL Browser-mode (.civmodellist) and Update-mode (.civmodelcards) containers.
    // querySelectorAll (not querySelector) so the Local Models grid — a second
    // .civmodellist in the DOM — also gets its cards updated after download/delete.
    const containers = [
        ...document.querySelectorAll('.civmodellist'),
        ...document.querySelectorAll('.civmodelcards')
    ];

    console.log('[updateCard] called:', modelNameWithSuffix, 'modelId:', modelId, 'containers:', containers.length, 'allowRefresh:', allowRefresh);

    if (containers.length === 0) {
        // No card containers visible — user is on a different tab. Queue for later.
        console.log('[updateCard] no containers — queued for later');
        pendingCardUpdates.add(modelNameWithSuffix);
        return;
    }

    let matchedCount = 0;
    containers.forEach((parentDiv, idx) => {
        const cards = parentDiv.querySelectorAll('.civmodelcard');
        console.log('[updateCard] container', idx, 'has', cards.length, 'cards');
        cards.forEach((card) => {
            let cardMatches = false;
            let matchMethod = '';

            if (modelId) {
                const cardModelId = card.getAttribute('data-model-id');
                cardMatches = cardModelId === modelId;
                if (cardMatches) matchMethod = 'data-model-id';
            }

            // Backward compatibility for cards rendered before data-model-id existed.
            if (!cardMatches) {
                const onclickAttr = card.getAttribute('onclick');
                cardMatches = !!(onclickAttr && onclickAttr.includes(`select_model('${modelName}', event)`));
                if (cardMatches) matchMethod = 'onclick';
            }

            if (!cardMatches) {
                return;
            }

            matchedCount += 1;
            console.log('[updateCard] MATCH via', matchMethod, '— adding', additionalClassName);
            statusClasses.forEach((statusClass) => card.classList.remove(statusClass));
            if (additionalClassName) {
                card.classList.add(additionalClassName);
            }
        });
    });

    // Fallback: if the card is not yet in the DOM snapshot, retry briefly.
    // If retries exhaust, queue for when the user returns to the tab (via MutationObserver).
    // NOTE: allowRefresh=false skips pressRefresh() — used for post-download triggers
    // to avoid expensive API re-fetch (100 items) when a single card is missing.
    if (matchedCount === 0) {
        const retryCount = cardSyncRetryState[modelNameWithSuffix] || 0;
        console.log('[updateCard] no match — retry', retryCount + 1, '/ 4');
        if (retryCount < 4) {
            cardSyncRetryState[modelNameWithSuffix] = retryCount + 1;
            setTimeout(() => updateCard(modelNameWithSuffix, allowRefresh), 120);
        } else {
            delete cardSyncRetryState[modelNameWithSuffix];
            console.log('[updateCard] exhausted retries — queued for tab-switch');
            // Instead of forcing a full refresh, queue for later tab-switch
            pendingCardUpdates.add(modelNameWithSuffix);
            if (allowRefresh) {
                pressRefresh();
            }
        }
    } else {
        delete cardSyncRetryState[modelNameWithSuffix];
        pendingCardUpdates.delete(modelNameWithSuffix);
        console.log('[updateCard] success — updated', matchedCount, 'card(s)');
    }

    const hideInstalledToggle =
        gradioApp().querySelector('#toggle5 input[type="checkbox"]') ||
        gradioApp().querySelector('#toggle5L input[type="checkbox"]');
    if (hideInstalledToggle) {
        hideInstalled(hideInstalledToggle.checked);
    }

    // A card whose status just changed (e.g. outdated -> installed after an update) must be
    // re-evaluated against the Local "Only models with updates" view filter.
    filterLocalOutdated();
}

// === VIDEO HOVER-TO-PLAY ===
// Attach hover-to-play listeners to a single card element
function attachVideoHoverPlay(card) {
    const video = card.querySelector('video.video-bg');
    if (!video || video._hoverPlayAttached) return;
    video._hoverPlayAttached = true;

    card.addEventListener('mouseenter', () => {
        video.play().catch(() => {});
    });
    card.addEventListener('mouseleave', () => {
        video.pause();
        video.currentTime = 0;
    });
}

// Observe the model list container for newly injected cards
(function initVideoHoverObserver() {
    function attachAll(root) {
        root.querySelectorAll('.civmodelcard').forEach(attachVideoHoverPlay);
    }

    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType !== 1) continue;
                if (node.classList && node.classList.contains('civmodelcard')) {
                    attachVideoHoverPlay(node);
                } else {
                    attachAll(node);
                }
            }
        }
    });

    function startObserver() {
        const container = document.querySelector('.civmodellist') || document.body;
        observer.observe(container, { childList: true, subtree: true });
        attachAll(container);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startObserver);
    } else {
        startObserver();
    }
})();

// Enables refresh with alt+enter and ctrl+enter
function keydownHandler(e) {
    var handled = false;

    if (e.key !== undefined) {
        if (e.key == 'Enter' && (e.metaKey || e.ctrlKey || e.altKey)) handled = true;
    } else if (e.keyCode !== undefined) {
        if (e.keyCode == 13 && (e.metaKey || e.ctrlKey || e.altKey)) handled = true;
    }

    if (handled) {
        var currentTabContent = get_uiCurrentTabContent();
        if (currentTabContent && currentTabContent.id === 'tab_civitai_interface') {
            var refreshButton = currentTabContent.querySelector('#refreshBtn');
            if (!refreshButton) {
                refreshButton = currentTabContent.querySelector('#refreshBtnL');
            }
            if (refreshButton) {
                refreshButton.click();
            }

            e.preventDefault();
        }
    }
}
document.addEventListener('keydown', keydownHandler);

// Function to adjust alignment of Filter Accordion
function adjustFilterBoxAndButtons() {
    const element = document.querySelector('#filterBox') || document.querySelector('#filterBoxL');
    if (!element) return;

    const childDiv = element.querySelector('div:nth-child(3)');
    if (!childDiv) return;

    const isLargeScreen = window.innerWidth >= 1250;
    const isMediumScreen = window.innerWidth < 1250 && window.innerWidth > 915;
    const isNarrowScreen = window.innerWidth < 800;
    const modelBlocks = document.querySelectorAll('#civitai_preview_html .model-block');
    const civitInfo = document.querySelector('.civitai-version-info');

    if (modelBlocks) {
        modelBlocks.forEach((modelBlock) => {
            if (isNarrowScreen) {
                modelBlock.style.flexWrap = 'wrap';
                modelBlock.style.justifyContent = 'center';
            } else {
                modelBlock.style.flexWrap = 'nowrap';
                modelBlock.style.justifyContent = 'flex-start';
            }
        });
    }
    if (civitInfo) {
        if (window.innerWidth < 900) {
            civitInfo.style.flexWrap = 'wrap';
        } else {
            civitInfo.style.flexWrap = 'nowrap';
        }
    }

    childDiv.style.marginLeft = isLargeScreen ? '0px' : isMediumScreen ? `${1250 - window.innerWidth}px` : '0px';
    element.style.justifyContent = isLargeScreen || isMediumScreen ? 'center' : 'flex-start';

    const pageBtn1 = document.querySelector('#pageBtn1');
    const pageBtn2 = document.querySelector('#pageBtn2');
    const pageBox = document.querySelector('#pageBox');
    const pageBoxMobile = document.querySelector('#pageBoxMobile');

    if (window.innerWidth < 530) {
        childDiv.style.width = '300px';
        if (pageBoxMobile) {
            pageBtn1 && pageBoxMobile.appendChild(pageBtn1);
            pageBtn2 && pageBoxMobile.appendChild(pageBtn2);
            pageBoxMobile.style.paddingBottom = '15px';
        }
    } else {
        childDiv.style.width = '400px';
        if (pageBox) {
            pageBtn1 && pageBox.insertBefore(pageBtn1, pageBox.firstChild);
            pageBtn2 && pageBox.appendChild(pageBtn2);
            pageBoxMobile.style.paddingBottom = '0px';
        }
    }
}

// Calls the function above whenever the window is resized
window.addEventListener('resize', adjustFilterBoxAndButtons);

// Function to trigger refresh button with extra checks for page slider
function pressRefresh() {
    setTimeout(() => {
        const input = document.querySelector('#pageSlider > div:nth-child(2) > div > input');
        if (document.activeElement === input) {
            function keydownHandler(event) {
                if (event.key === 'Enter' || event.keyCode === 13) {
                    input.blur();
                    input.removeEventListener('keydown', keydownHandler);
                    input.removeEventListener('blur', blurHandler);
                }
            }

            function blurHandler() {
                input.removeEventListener('keydown', keydownHandler);
                input.removeEventListener('blur', blurHandler);
            }

            input.addEventListener('keydown', keydownHandler);
            input.addEventListener('blur', blurHandler);

            return;
        }
        let output = gradioApp().querySelector('#page_slider_trigger textarea');
        if (output) {
            const randomNumber = Math.floor(Math.random() * 1000);
            const paddedNumber = String(randomNumber).padStart(3, '0');
            output.value = paddedNumber;
            updateInput(output);
        }
    }, 200);
}

// Update SVG Icons based on dark theme or light theme
function updateSVGIcons() {
    const isDark = document.body.classList.contains('dark');
    const filterIconUrl = isDark
        ? 'https://gistcdn.githack.com/BlafKing/a20124cedafad23d4eecc1367ec22896/raw/04a4dae0771353377747dadf57c91d55bf841bed/filter-light.svg'
        : 'https://gistcdn.githack.com/BlafKing/686c3438f5d0d13e7e47135f25445ef3/raw/46477777faac7209d001829a171462d9a2ff1467/filter-dark.svg';
    const searchIconUrl = isDark
        ? 'https://gistcdn.githack.com/BlafKing/3f95619089bac3b4fd5470a986e1b3bb/raw/ebaa9cceee3436711eb560a7a65e151f1d651c6a/search-light.svg'
        : 'https://gistcdn.githack.com/BlafKing/57573592d5857e102a4bfde852f62639/raw/aa213e9e82d705651603507e26545eb0ffe60c90/search-dark.svg';

    if (isDark) {
    }

    const element = document.querySelector('#filterBox, #filterBoxL');
    const childDiv = element?.querySelector('div:nth-child(3)');

    if (childDiv) {
        childDiv.style.cssText = `box-shadow: ${isDark ? '#ffffff' : '#000000'} 0px 0px 2px 0px; display: none;`;
    }

    const style = document.createElement('style');
    style.innerHTML = `
        #filterBox > div:nth-child(2) > span:nth-child(2)::before,
        #filterBoxL > div:nth-child(2) > span:nth-child(2)::before {
            background: url('${filterIconUrl}') no-repeat center center;
            background-size: contain;
        }
        #refreshBtn > img,
        #refreshBtnL > img {
            content: url('${searchIconUrl}');
        }

        /* Gradio 4 */
        #filterBox > button:nth-child(2),
        #filterBoxL > button:nth-child(2) {
            background: url('${filterIconUrl}') no-repeat center center !important;
            background-size: 22px !important;
        }
        #filterBox > button:nth-child(2) > span,
        #filterBoxL > button:nth-child(2) > span {
            visibility: hidden;
        }
    `;
    document.head.appendChild(style);
}

// Creates a tooltip if the user wants to filter liked models without a personal API key
function createTooltip(element, hover_element, insertText) {
    if (element) {
        const tooltip = document.createElement('div');
        tooltip.className = 'browser_tooltip';
        tooltip.textContent = insertText;
        tooltip.style.cssText = 'display: none; text-align: center; white-space: pre;';

        hover_element.addEventListener('mouseover', () => {
            tooltip.style.display = 'block';
        });
        hover_element.addEventListener('mouseout', () => {
            tooltip.style.display = 'none';
        });
        element.appendChild(tooltip);
    }
}

// Function that closes filter dropdown if clicked outside the dropdown
function setupClickOutsideListener() {
    var filterBox = document.getElementById('filterBoxL') || document.getElementById('filterBox');
    if (!filterBox) return;
    var filterButton = filterBox.children[1];
    var dropDown = filterBox.getElementsByTagName('div')[2];

    function clickOutsideHandler(event) {
        var target = event.target;
        if (!filterBox.contains(target)) {
            if (!dropDown.contains(target)) {
                if (filterButton.className.endsWith('open')) {
                    filterButton.click();
                }
            }
        }
    }
    document.addEventListener('click', clickOutsideHandler);
}

// Create hyperlink in settings to CivitAI account settings
function createLink(infoElement) {
    const existingText = '(You can create your own API key in your CivitAI account settings, this required for some downloads. Requires UI reload)';
    const linkText = 'CivitAI account settings';

    const [textBefore, textAfter] = existingText.split(linkText);

    const link = document.createElement('a');
    link.textContent = linkText;
    link.href = 'https://civitai.com/user/account';
    link.target = '_blank';

    while (infoElement.firstChild) infoElement.removeChild(infoElement.firstChild);

    infoElement.appendChild(document.createTextNode(textBefore));
    infoElement.appendChild(link);
    infoElement.appendChild(document.createTextNode(textAfter));
}

// Create the accordion dropdown inside the settings tab
function createAccordion(containerDiv, subfolders, name, id_name) {
    if (containerDiv == null) {
        return;
    }
    var accordionContainer = document.createElement('div');
    accordionContainer.id = id_name;
    accordionContainer.className = 'settings-accordion';
    var toggleButton = document.createElement('button');
    toggleButton.id = 'accordionToggle';
    toggleButton.innerHTML = name + '<div style="transition: transform 0.15s; transform: rotate(90deg)">▼</div>';
    toggleButton.onclick = function () {
        accordionDiv.style.display = accordionDiv.style.display === 'none' ? 'block' : 'none';
        toggleButton.lastChild.style.transform = accordionDiv.style.display === 'none' ? 'rotate(90deg)' : 'rotate(0)';
    };

    accordionContainer.appendChild(toggleButton);
    var accordionDiv = document.createElement('div');
    accordionDiv.classList.add('accordion');
    if (subfolders && subfolders.length > 0) {
        accordionDiv.append(...subfolders);
    }

    accordionDiv.style.display = 'none'; // Initially hidden
    accordionContainer.appendChild(accordionDiv);
    containerDiv.appendChild(accordionContainer);
}

// Adds a button to the cards in txt2img and img2img
function createCivitAICardButtons() {
    const copyButton = document.querySelector('.copy-path-button');
    let fontSize = '1.8rem';
    if (!copyButton) {
        const editButton = document.querySelector('.edit-button');
        if (editButton) {
            const originalDisplay = editButton.parentElement.style.display;
            editButton.parentElement.style.display = 'flex';
            const editButtonBeforeStyle = window.getComputedStyle(editButton, ':before');
            fontSize = editButtonBeforeStyle.getPropertyValue('font-size');
            editButton.parentElement.style.display = originalDisplay;
        }
    }

    const checkForCardDivs = setInterval(() => {
        const cardDivs = document.querySelectorAll('.card');
        if (cardDivs.length > 0) {
            clearInterval(checkForCardDivs);

            cardDivs.forEach((cardDiv) => {
                const buttonRow = cardDiv.querySelector('.button-row');
                if (!buttonRow) return;

                buttonRow.addEventListener('click', function (event) {
                    event.stopPropagation();
                });

                const modelName = cardDiv.querySelector('.actions .name')?.textContent.trim();
                if (!modelName) return;

                // Searched across the whole card (not just buttonRow): the themed layout
                // relocates these buttons into .civitai-neo-bottom-actions, so a buttonRow-only
                // check would miss them there and create duplicates on every re-scan.
                let gotoBtn = cardDiv.querySelector('.goto-civitbrowser.card-button');
                if (!gotoBtn) {
                    gotoBtn = document.createElement('div');
                    gotoBtn.className = 'goto-civitbrowser card-button';
                    const svgIcon = createSVGIcon(fontSize);
                    gotoBtn.appendChild(svgIcon);

                    gotoBtn.onclick = () => modelInfoPopUp(modelName, cardDiv.parentElement.id);
                    buttonRow.insertBefore(gotoBtn, buttonRow.firstChild);
                }

                ensureTriggerButton(buttonRow, fontSize);

                if (isNativeCardThemeActive()) {
                    applyNativeCardTheme(cardDiv, buttonRow, modelName, fontSize);
                } else {
                    applyNativeCardBadges(cardDiv, buttonRow, modelName);
                }
            });
        }
    }, 200);

    setTimeout(() => {
        clearInterval(checkForCardDivs);
    }, 5000);
}

// === Native card badges/actions (base model, LoRA category, trigger words) ===
// Data comes from a Python-built map (civitai_file_manage.build_native_card_badge_map),
// fetched once via requestNativeBadgeData() and cached in window.__civitaiNativeBadges.
function requestNativeBadgeData() {
    const trigger = gradioApp().querySelector('#native_badge_trigger textarea');
    if (!trigger) return;
    trigger.value = String(Date.now());
    updateInput(trigger);
}

// Auto-organized LoRAs are indexed both by plain filename and "Subfolder/filename" on the
// Python side (build_native_card_badge_map), but tries the last path segment too in case
// WebUI ever displays a nesting depth/format we didn't anticipate.
function lookupBadgeInfo(modelName) {
    const badges = window.__civitaiNativeBadges || {};
    return badges[modelName] || badges[modelName.split('/').pop()];
}

function isNativeCardThemeActive() {
    return document.body.classList.contains('civitai-neo-card-theme');
}

// Applies the "Settings → CivitAI-style card theme" toggle as a body class so CSS can
// scope the whole redesign; re-run createCivitAICardButtons() so already-rendered cards
// pick it up without a full page reload.
function syncNativeCardThemeSetting() {
    const checkbox = gradioApp().querySelector('#setting_civitai_native_card_theme input[type=checkbox]');
    if (!checkbox) return;
    const apply = () => {
        document.body.classList.toggle('civitai-neo-card-theme', checkbox.checked);
        createCivitAICardButtons();
    };
    apply();
    checkbox.addEventListener('change', apply);
}

function ensureTriggerButton(buttonRow, fontSize) {
    const cardDiv = buttonRow.closest('.card');
    let triggerBtn = cardDiv?.querySelector('.civitai-native-trigger-btn');
    if (triggerBtn) return triggerBtn;

    const modelName = cardDiv?.querySelector('.actions .name')?.textContent.trim();
    const info = modelName ? lookupBadgeInfo(modelName) : null;
    if (!info || !info.triggerWords || !info.triggerWords.length) return null;

    triggerBtn = document.createElement('div');
    triggerBtn.className = 'civitai-native-trigger-btn card-button';
    triggerBtn.title = 'Send trigger words to prompt';
    triggerBtn.textContent = '🏷️';
    triggerBtn.style.fontSize = fontSize;
    triggerBtn.onclick = (event) => {
        event.stopPropagation();
        sendTagsToPrompt(info.triggerWords.join(', '));
    };
    buttonRow.appendChild(triggerBtn);
    return triggerBtn;
}

// Compact mode (theme OFF): small chips inside the existing native button-row.
function applyNativeCardBadges(cardDiv, buttonRow, modelName) {
    // Clean up leftovers from a live theme-toggle-off (no page reload) so the two badge
    // layouts never coexist on the same card. ALL button-row children (native buttons
    // included) were MOVED (not cloned) into .civitai-neo-bottom-actions, so rescue every
    // one of them back into buttonRow before removing their themed container, or they'd be
    // deleted along with it.
    const themedBottom = cardDiv.querySelector('.civitai-neo-bottom');
    if (themedBottom) {
        const actionsRow = themedBottom.querySelector('.civitai-neo-bottom-actions');
        if (actionsRow) {
            Array.from(actionsRow.children).forEach((btn) => buttonRow.appendChild(btn));
        }
        themedBottom.remove();
    }
    cardDiv.querySelector('.civitai-neo-top-row')?.remove();

    const info = lookupBadgeInfo(modelName);
    if (!info) return;

    if (info.baseModelShort && !buttonRow.querySelector('.civitai-native-base-badge')) {
        const baseBadge = document.createElement('div');
        baseBadge.className = 'civitai-native-base-badge';
        baseBadge.textContent = info.baseModelShort;
        baseBadge.title = info.baseModel || info.baseModelShort;
        buttonRow.insertBefore(baseBadge, buttonRow.firstChild);
    }

    if (info.loraCategory && !buttonRow.querySelector('.civitai-native-lora-badge')) {
        const catBadge = document.createElement('div');
        catBadge.className = `civitai-native-lora-badge lora-category-badge ${info.loraCategory.toLowerCase()}`;
        catBadge.textContent = info.loraCategory;
        buttonRow.insertBefore(catBadge, buttonRow.firstChild);
    }
}

function getCardTypeLabel(parentId) {
    const id = (parentId || '').toLowerCase();
    if (id.includes('lora')) return 'LoRA';
    if (id.includes('checkpoint')) return 'Checkpoint';
    if (id.includes('hypernetwork')) return 'Hypernetwork';
    if (id.includes('textual') || id.includes('embedding')) return 'Embedding';
    return '';
}

// CivitAI-style theme (theme ON): badges top row, name + ALL action buttons (native ones —
// copy path, edit metadata, refresh — plus ours — goto-civitbrowser, trigger-word inject) in
// a gradient bar at the bottom. Buttons are relocated (not cloned) out of the native
// button-row into our own bottom bar so nothing is left floating at the top/side.
function applyNativeCardTheme(cardDiv, buttonRow, modelName, fontSize) {
    cardDiv.style.position = cardDiv.style.position || 'relative';
    const info = lookupBadgeInfo(modelName) || {};
    const displayName = info.displayName || modelName;

    // Rebuilt (not just created-once) on every scan: badge data (window.__civitaiNativeBadges)
    // arrives asynchronously, and cards with far more entries than others (typically LoRA,
    // since libraries usually have many more LoRAs than checkpoints) are more likely to get
    // their first pass in before the fetch lands. A create-once guard would otherwise lock
    // that card into an empty badge forever.
    let topRow = cardDiv.querySelector('.civitai-neo-top-row');
    if (!topRow) {
        topRow = document.createElement('div');
        topRow.className = 'civitai-neo-top-row';
        cardDiv.appendChild(topRow);
    }
    topRow.innerHTML = '';

    // "Type | BaseModel" combined into one pill (e.g. "Checkpoint | ANI"), mirroring the
    // .model-type-badge convention already used on our own Browser/Local cards, rather than
    // two separate pills fighting for space.
    const typeLabel = getCardTypeLabel(cardDiv.parentElement.id);
    if (typeLabel || info.baseModelShort) {
        const typeBadge = document.createElement('span');
        typeBadge.className = 'civitai-neo-badge civitai-neo-badge-type';
        typeBadge.textContent = info.baseModelShort ? `${typeLabel} | ${info.baseModelShort}` : typeLabel;
        if (info.baseModelShort) typeBadge.title = info.baseModel || info.baseModelShort;
        topRow.appendChild(typeBadge);
    }

    if (info.loraCategory) {
        const catBadge = document.createElement('span');
        catBadge.className = `civitai-neo-badge lora-category-badge ${info.loraCategory.toLowerCase()}`;
        catBadge.textContent = info.loraCategory;
        topRow.appendChild(catBadge);
    }

    let bottom = cardDiv.querySelector('.civitai-neo-bottom');
    if (!bottom) {
        bottom = document.createElement('div');
        bottom.className = 'civitai-neo-bottom';

        // Action buttons sit above the name/version block.
        const actionsRow = document.createElement('div');
        actionsRow.className = 'civitai-neo-bottom-actions';
        // buttonRow's own stopPropagation listener (added in createCivitAICardButtons)
        // stays behind on the native button-row when its children are relocated here —
        // without re-adding it, clicks on any button (goto-civitbrowser, trigger-word,
        // native edit/copy/refresh) bubble up to the card's native click handler, which
        // inserts the LoRA/embedding into the prompt as if the card itself was clicked.
        actionsRow.addEventListener('click', function (event) {
            event.stopPropagation();
        });
        bottom.appendChild(actionsRow);

        const titleBlock = document.createElement('div');
        titleBlock.className = 'civitai-neo-title-block';

        const nameEl = document.createElement('div');
        nameEl.className = 'civitai-neo-name';
        titleBlock.appendChild(nameEl);

        const versionEl = document.createElement('div');
        versionEl.className = 'civitai-neo-version';
        titleBlock.appendChild(versionEl);

        bottom.appendChild(titleBlock);

        cardDiv.appendChild(bottom);
    }

    const nameEl = bottom.querySelector('.civitai-neo-name');
    nameEl.textContent = displayName;
    nameEl.title = displayName;

    const versionEl = bottom.querySelector('.civitai-neo-version');
    versionEl.textContent = info.version || '';
    versionEl.style.display = info.version ? '' : 'none';

    // Relocate whatever is currently in button-row (native buttons + ours) into our own
    // bottom bar — runs every scan so buttons that appear later (async-rendered edit/copy
    // buttons) still get picked up, not just on first creation.
    const actionsRow = bottom.querySelector('.civitai-neo-bottom-actions');
    Array.from(buttonRow.children).forEach((el) => actionsRow.appendChild(el));
}

function createSVGIcon(fontSize) {
    const svgIcon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svgIcon.setAttribute('width', fontSize);
    svgIcon.setAttribute('height', fontSize);
    svgIcon.setAttribute('viewBox', '75 85 350 350');
    svgIcon.setAttribute('fill', 'white');
    if (fontSize == '1.8rem') {
        svgIcon.setAttribute('style', 'margin-top: -2px');
    }
    svgIcon.innerHTML = `
        <path d="M 352.79 218.85 L 319.617 162.309 L 203.704 162.479 L 146.28 259.066 L 203.434 355.786 L 319.373 355.729 L 352.773 299.386 L 411.969 299.471 L 348.861 404.911 L 174.065 404.978 L 87.368 259.217 L 174.013 113.246 L 349.147 113.19 L 411.852 218.782 L 352.79 218.85 Z"/>
        <path d="M 304.771 334.364 L 213.9 334.429 L 169.607 259.146 L 214.095 183.864 L 305.132 183.907 L 330.489 227.825 L 311.786 259.115 L 330.315 290.655 Z M 278.045 290.682 L 259.294 259.18 L 278.106 227.488 L 240.603 227.366 L 221.983 259.128 L 240.451 291.026 Z"/>
    `;

    return svgIcon;
}

function addOnClickToButtons() {
    const tabs = ['img2img_extra_tabs', 'txt2img_extra_tabs'].map((id) => document.getElementById(id));
    const buttonIds = ['txt2img_checkpoints_extra_refresh', 'img2img_checkpoints_extra_refresh', 'txt2img_extra_refresh', 'img2img_extra_refresh'];

    buttonIds.forEach((buttonId) => {
        let button = document.getElementById(buttonId);
        if (button) {
            button.addEventListener('click', (event) => {
                createCivitAICardButtons(button);
                requestNativeBadgeData();
            });
        }
    });

    tabs.forEach((tab) => {
        if (tab) {
            const buttons = tab.querySelectorAll('div > button:not(:first-child)');
            buttons.forEach((button) => {
                button.addEventListener('click', (event) => {
                    createCivitAICardButtons(button);
                    requestNativeBadgeData();
                });
            });
        }
    });
}

function modelInfoPopUp(modelName = null, content_type = null, no_message = false) {
    const sendToBrowserElement = gradioApp().querySelector('#setting_civitai_send_to_browser input');
    let sendToBrowser = false;
    if (sendToBrowserElement) {
        sendToBrowser = sendToBrowserElement.checked;
    }
    if (modelName) {
        try {
            select_model(modelName, null, true, content_type, sendToBrowser);
        } catch (e) {
            console.warn('[CivitAI Browser] select_model error:', e);
        }
    }
    if (sendToBrowser) {
        const tabNav = document.querySelector('.tab-nav');
        const buttons = tabNav ? tabNav.querySelectorAll('button') : [];
        let browserTabFound = false;
        for (const button of buttons) {
            if (button.textContent.includes('Browser+') || button.textContent.includes('CivitAI Browser')) {
                button.click();
                browserTabFound = true;
                const tabId = document.querySelector('#tab_civitai_interface_neo')
                    ? '#tab_civitai_interface_neo'
                    : '#tab_civitai_interface';
                const firstButton = document.querySelector(`${tabId} > div > div > div > button`);
                if (firstButton) {
                    firstButton.click();
                }
                break;
            }
        }
        if (!browserTabFound) {
            createCivitaiOverlay(no_message);
        }
    } else {
        createCivitaiOverlay(no_message);
    }
}

function createCivitaiOverlay(noMessage = false) {
    // Remove existing overlay if present
    const existingOverlay = document.querySelector('.civitai-overlay');
    if (existingOverlay) {
        existingOverlay.remove();
    }

    // Create overlay container
    const overlay = document.createElement('div');
    overlay.className = 'civitai-overlay';
    overlay.setAttribute('data-overlay-type', 'model-info');

    // Create inner content container
    const inner = document.createElement('div');
    inner.className = 'civitai-overlay-inner';

    // Create loading message if needed
    if (!noMessage) {
        const loadingMessage = document.createElement('div');
        loadingMessage.className = 'civitai-overlay-text';
        loadingMessage.textContent = 'Loading model info, please wait!';
        inner.appendChild(loadingMessage);
    }

    // Add event listeners
    overlay.addEventListener('click', handleOverlayClick);
    document.addEventListener('keydown', handleOverlayKeyPress);

    // Prevent body scroll
    document.body.style.overflow = 'hidden';

    // Append to DOM
    overlay.appendChild(inner);
    document.body.appendChild(overlay);

    // Trigger animation after DOM is ready
    setTimeout(() => {
        overlay.classList.add('show');
    }, 10);

    // Store reference for cleanup
    window.currentCivitaiOverlay = overlay;
}

// Handle overlay click events
function handleOverlayClick(event) {
    if (event.target.classList.contains('civitai-overlay')) {
        hideCivitaiOverlay();
    }
}
// Handle overlay keyboard events
function handleOverlayKeyPress(event) {
    if (event.key === 'Escape') {
        // Check if image viewer is open - if so, don't close overlay
        if (currentViewerOverlay && currentViewerOverlay.classList.contains('active')) {
            return; // Let image viewer handle ESC
        }
        hideCivitaiOverlay();
    }
}

function hideCivitaiOverlay() {
    const overlay = document.querySelector('.civitai-overlay');
    if (overlay) {
        // Start fade out animation
        overlay.classList.remove('show');

        // Wait for animation to complete before removing from DOM
        setTimeout(() => {
        // Remove event listeners
        overlay.removeEventListener('click', handleOverlayClick);
        document.removeEventListener('keydown', handleOverlayKeyPress);

        // Remove from DOM
        overlay.remove();

        // Restore body scroll
        document.body.style.overflow = 'auto';

        // Clear reference
        window.currentCivitaiOverlay = null;
        }, 300); // Match the CSS transition duration
    }
}

function inputHTMLPreviewContent(html_input) {
    const inner = document.querySelector('.civitai-overlay-inner');
    if (!inner) return;

    let startIndex = html_input.indexOf("'value': '");
    if (startIndex !== -1) {
        startIndex += "'value': '".length;
        let endIndex = html_input.indexOf(", 'placeholder'", startIndex);
        if (endIndex === -1) {
            endIndex = html_input.indexOf("', 'type': None,", startIndex);
        }
        if (endIndex !== -1) {
            let extractedText = html_input.substring(startIndex, endIndex);
            const modelIdNotFound = extractedText.includes('>Model ID not found.<br>The');

            // Clean up the HTML content
            extractedText = extractedText.replace(/\\n\s*</g, '<');
            extractedText = extractedText.replace(/\\n/g, ' ');
            extractedText = extractedText.replace(/\\t/g, '');
            extractedText = extractedText.replace(/\\'/g, "'");

            // Hide loading text
            const overlayText = document.querySelector('.civitai-overlay-text');
            if (overlayText) {
                overlayText.style.display = 'none';
            }

            // Create content container
            const modelInfo = document.createElement('div');
            modelInfo.innerHTML = extractedText;
            modelInfo.style.opacity = '0';
            modelInfo.style.transform = 'translateY(20px)';
            modelInfo.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            inner.appendChild(modelInfo);

            // Allow inner container to expand to content height
            inner.style.height = 'auto';

            // Animate content appearance
            requestAnimationFrame(() => {
                modelInfo.style.opacity = '1';
                modelInfo.style.transform = 'translateY(0)';
            });

            // Initialize description toggle
            setTimeout(() => initDescriptionToggle('preview-'), 50);
        }
    }
}

function metaToTxt2Img(event, type, element) {
    const selection = window.getSelection();
    if (selection.toString().length > 0) {
        return;
    }
    const isAppend = event && event.shiftKey;
    const genButton = gradioApp().querySelector('#txt2img_extra_tabs > div > button');
    let input = element.querySelector('dd').textContent;
    let inf;
    if (input.endsWith(',')) {
        inf = input + ' ';
    } else {
        inf = input + ', ';
    }
    let is_positive = false;
    let is_negative = false;
    switch (type) {
        case 'Prompt':
            is_positive = true;
            break;
        case 'Negative prompt':
            inf = 'Negative prompt: ' + inf;
            is_negative = true;
            break;
        case 'Seed':
            inf = 'Seed: ' + inf;
            inf = inf + inf + inf;
            break;
        case 'Size':
            inf = 'Size: ' + inf;
            inf = inf + inf + inf;
            break;
        case 'Model':
            inf = 'Model: ' + inf;
            inf = inf + inf + inf;
            break;
        case 'Clip skip':
            inf = 'Clip skip: ' + inf;
            inf = inf + inf + inf;
            break;
        case 'Sampler':
            inf = 'Sampler: ' + inf;
            inf = inf + inf + inf;
            break;
        case 'Steps':
            inf = 'Steps: ' + inf;
            inf = inf + inf + inf;
            break;
        case 'CFG scale':
            inf = 'CFG scale: ' + inf;
            inf = inf + inf + inf;
            break;
    }
    const prompt = gradioApp().querySelector('#txt2img_prompt textarea');
    const neg_prompt = gradioApp().querySelector('#txt2img_neg_prompt textarea');
    const cfg_scale = gradioApp().querySelector('#txt2img_cfg_scale > div:nth-child(2) > div > input');
    if (!genButton || !prompt || !neg_prompt || !cfg_scale) return;
    let final = '';
    let cfg = 'CFG scale: ' + cfg_scale.value + ', ';
    let prompt_addon = cfg + cfg + cfg;
    if (is_positive) {
        if (isAppend) {
            const existing = prompt.value.trimEnd().replace(/,\s*$/, '');
            const combined = existing ? existing + ', ' + input : input;
            final = combined + '\nNegative prompt: ' + neg_prompt.value + '\n' + prompt_addon;
        } else {
            final = inf + '\nNegative prompt: ' + neg_prompt.value + '\n' + prompt_addon;
        }
    } else if (is_negative) {
        if (isAppend) {
            const existingNeg = neg_prompt.value.trimEnd().replace(/,\s*$/, '');
            const combinedNeg = existingNeg ? existingNeg + ', ' + input : input;
            final = prompt.value + '\nNegative prompt: ' + combinedNeg + '\n' + prompt_addon;
        } else {
            final = prompt.value + '\n' + inf + '\n' + prompt_addon;
        }
    } else {
        final = prompt.value + '\nNegative prompt: ' + neg_prompt.value + '\n' + inf;
    }
    genInfo_to_txt2img(final, false);
    hideCivitaiOverlay();
    sendClick(genButton);
}

// Creates a list of the selected models.
// The Browser and Local Models grids both render .model-checkbox cards, so the
// selection is scoped per grid: checkboxes inside #local_list_html feed the Local
// arrays (read by updateSelectedLocalModels), everything else feeds the Browser
// arrays (read by "Download all selected" via #selected_model_list). Without this
// split, a card checked in Local Models leaked into the Browser's download.
var selectedModels = [];
var selectedTypes = [];
var selectedModelsLocal = [];
var selectedTypesLocal = [];

function _syncBrowserSelectionInputs() {
    const selectedModelList = gradioApp().querySelector('#selected_model_list textarea');
    const selectedTypeList = gradioApp().querySelector('#selected_type_list textarea');

    if (selectedModelList) {
        selectedModelList.value = JSON.stringify(selectedModels);
        updateInput(selectedModelList);
    }
    if (selectedTypeList) {
        selectedTypeList.value = JSON.stringify(selectedTypes);
        updateInput(selectedTypeList);
    }
    syncUpdateBtn();
}

// Reset one grid only. Browser refresh/pagination used to clear both in-memory
// arrays while leaving #selected_model_list stale, allowing old Browser ids to be
// resolved against whatever happened to be loaded under the Local filters.
function clearModelSelection(scope = 'browser') {
    if (scope === 'local') {
        selectedModelsLocal = [];
        selectedTypesLocal = [];
        return;
    }

    selectedModels = [];
    selectedTypes = [];
    _browserCheckboxes().forEach((checkbox) => { checkbox.checked = false; });
    _syncBrowserSelectionInputs();
}

// True when the toggled checkbox element lives in the Local Models grid.
// Gradio 4 may wrap HTML content in ways that break el.closest('#local_list_html'),
// so we also rely on an explicit data-local marker stamped by the Python renderer.
function _isLocalCheckbox(el) {
    if (!el) return false;
    if (el.dataset && el.dataset.local === 'true') return true;
    return !!(el.closest && el.closest('#local_list_html'));
}

function multi_model_select(modelName, modelType, isChecked, el) {
    if (arguments.length === 0) {
        clearModelSelection('browser');
        return;
    }
    const isLocal = _isLocalCheckbox(el);
    // Defensive: if the Python renderer stamped data-local="true" but we still
    // failed to detect it as local, log the mismatch so we can diagnose paginated
    // selection bugs without needing a live reproduction.
    const hasLocalMarker = !!(el && el.dataset && el.dataset.local === 'true');
    if (hasLocalMarker && !isLocal) {
        console.warn('[CivitAI Browser Neo] checkbox has data-local=true but _isLocalCheckbox returned false', el);
    }
    const models = isLocal ? selectedModelsLocal : selectedModels;
    const types  = isLocal ? selectedTypesLocal  : selectedTypes;

    if (isChecked) {
        if (!models.includes(modelName)) {
            models.push(modelName);
        }
        types.push(modelType);
    } else {
        var modelIndex = models.indexOf(modelName);
        if (modelIndex > -1) {
            models.splice(modelIndex, 1);
        }
        var typesIndex = types.indexOf(modelType);
        if (typesIndex > -1) {
            types.splice(typesIndex, 1);
        }
    }

    console.log(`[CivitAI Browser Neo] multi_model_select: isLocal=${isLocal} modelName=${modelName} isChecked=${isChecked} localCount=${selectedModelsLocal.length} browserCount=${selectedModels.length}`);

    // Local selection is read straight off selectedModelsLocal — no Gradio textbox sync.
    if (isLocal) {
        return;
    }

    _syncBrowserSelectionInputs();
}

// Local Models tab: update only the checked (outdated) cards. Reads the
// selectedModelsLocal array (populated by the card checkboxes via multi_model_select)
// and feeds the existing update_selected_trigger → update_selected_models pipeline.
function updateSelectedLocalModels() {
    console.log('[CivitAI Browser Neo] updateSelectedLocalModels called:', selectedModelsLocal);
    if (!selectedModelsLocal || selectedModelsLocal.length === 0) {
        alert('Select one or more outdated models (checkbox on the cards) to update.');
        return;
    }
    const trigger = gradioApp().querySelector('#update_selected_trigger textarea');
    if (!trigger) {
        console.warn('[CivitAI Browser Neo] updateSelectedLocalModels: #update_selected_trigger textarea not found');
        return;
    }
    setCivDownloadOrigin('local');
    trigger.value = JSON.stringify(selectedModelsLocal);
    updateInput(trigger);
}

function sendClick(location) {
    const clickEvent = new MouseEvent('click', {
        view: window,
        bubbles: true,
        cancelable: true,
    });
    location.dispatchEvent(clickEvent);
}

let currentDlCancelled = false;

function cancelCurrentDl() {
    currentDlCancelled = true;
}

let allDlCancelled = false;

function cancelAllDl() {
    allDlCancelled = true;
}

function setSortable() {
    new Sortable(document.getElementById('queue_list'), {
        onEnd: function (evt) {
            const gradio_input = ((document.querySelector('#civitai_dl_list.prose') || document.querySelector('#civitai_dl_list') || {}).innerHTML || '');
            const gradio_html = gradioApp().querySelector('#queue_html_input textarea');
            let output = gradioApp().querySelector('#arrange_dl_id textarea');
            output.value = evt.item.getAttribute('dl_id') + '.' + evt.newIndex;
            updateInput(output);
            gradio_html.value = gradio_input;
            updateInput(gradio_html);
        },
    });
}

function cancelQueueDl() {
    const cancelBtn = gradioApp().querySelector('#html_cancel_input textarea');
    const randomNumber = Math.floor(Math.random() * 1000);
    const paddedNumber = String(randomNumber).padStart(3, '0');
    cancelBtn.value = paddedNumber;
    updateInput(cancelBtn);
    cancelBtn;
}

// Creates a setInterval-equivalent backed by a Web Worker so it runs
// unthrottled even when the browser tab is in the background.
function _createWorkerInterval(callback, ms) {
    const code = `var id;self.onmessage=function(e){if(e.data==='start'){id=setInterval(function(){self.postMessage('tick');},${ms});}else{clearInterval(id);self.close();}};`;
    const blob = new Blob([code], { type: 'application/javascript' });
    const url = URL.createObjectURL(blob);
    const worker = new Worker(url);
    worker.onmessage = function() { callback(); };
    worker.postMessage('start');
    worker._url = url;
    worker.stop = function() { worker.postMessage('stop'); URL.revokeObjectURL(url); };
    return worker;
}

// "Only models with updates" view filter on the Local Models grid. Pure client-side:
// hides every card the grid did NOT mark as outdated. Re-applied after each render so it
// works both as a pre-filter (checked before Load) and a post-filter (toggled after Load).
function filterLocalOutdated() {
    const cb = document.querySelector('#localOnlyUpdates input[type="checkbox"]');
    const onlyOutdated = cb ? cb.checked : false;
    const grid = document.querySelector('#local_list_html');
    if (!grid) return;
    grid.querySelectorAll('figure.civmodelcard').forEach(card => {
        const isOutdated = card.classList.contains('civmodelcardoutdated');
        card.style.display = (onlyOutdated && !isOutdated) ? 'none' : '';
    });
}

// Per-tab download progress gating. Each queue item carries a dl_origin attribute
// ('browser' | 'local'), written by Python when the item was enqueued. The origin of
// the item that is DOWNLOADING NOW drives which tab shows progress — so queued items
// from different tabs hand the bars over correctly, and clicking an update in one tab
// can't hijack the bar of a download already running from the other.
window.civDownloadOrigin = window.civDownloadOrigin || 'browser';
function setCivDownloadOrigin(origin) {
    window.civDownloadOrigin = origin;
    const b = document.body;
    if (!b) return;
    b.classList.toggle('civ-dl-origin-local', origin === 'local');
    b.classList.toggle('civ-dl-origin-browser', origin === 'browser');
}

// Origin of the queue item currently downloading (the active item sits in the
// non-queue list while still having the civitai_dl_item class).
function _currentDlOrigin() {
    const list = document.getElementById('civitai_dl_list');
    const item = list && (list.querySelector('.civitai_nonqueue_list .civitai_dl_item')
                          || list.querySelector('.civitai_dl_item'));
    return (item && item.getAttribute('dl_origin')) || 'browser';
}

// Mirror the live #DownloadProgress bar into the Local Models tab, so updates started
// from there (Update to latest / Update selected) show progress without switching tabs.
function setLocalDownloadProgressBar(attempt) {
    attempt = attempt || 0;
    const target = document.querySelector('#local_download_progress');
    if (!target) return;

    // Wait until the native progress bar exists (download starts async), then mirror it.
    // Give up after ~10s so an update that queues nothing (already on latest) doesn't
    // leave a retry loop running forever.
    const container0 = document.querySelector('#DownloadProgress');
    const bar0 = container0 && container0.querySelector('.progress-bar');
    if (!bar0 || !bar0.style.width) {
        if (attempt < 20) {
            setTimeout(() => setLocalDownloadProgressBar(attempt + 1), 500);
        }
        return;
    }

    // Only mirror downloads whose queue item originated in the Local tab. Checked after
    // the bar exists so the item's dl_origin attribute is already in the DOM.
    if (_currentDlOrigin() !== 'local') {
        target.innerHTML = '<div style="min-height:0px;"></div>';
        return;
    }

    const render = (pct, label, state) => {
        const colour = state === 'failed' ? '#b54a4a' : (state === 'done' ? '#3a8f4f' : '#3b6fb5');
        target.innerHTML =
            '<div style="margin:6px 0;">' +
              '<div style="font-size:12px;opacity:.8;margin-bottom:3px;">' + (label || '') + '</div>' +
              '<div style="background:#2a2a2a;border-radius:6px;overflow:hidden;height:20px;">' +
                '<div style="height:100%;width:' + pct + '%;background:' + colour + ';' +
                'transition:width .2s;text-align:center;color:#fff;font-size:12px;line-height:20px;">' +
                  pct.toFixed(1) + '%' +
                '</div>' +
              '</div>' +
            '</div>';
    };

    const clearSoon = () => setTimeout(() => {
        const t = document.querySelector('#local_download_progress');
        if (t) t.innerHTML = '<div style="min-height:0px;"></div>';
    }, 3000);

    let sawProgress = false;
    const worker = _createWorkerInterval(() => {
        const container = document.querySelector('#DownloadProgress');
        const bar = container && container.querySelector('.progress-bar');
        const innerEl = container && container.querySelector('.progress-level-inner');
        if (!bar || !bar.style.width) {
            // Native bar gone/reset. If we'd already shown progress, the download finished
            // (Gradio clears #DownloadProgress on completion) — finalize so the bar doesn't
            // stay stuck at the last percentage.
            if (sawProgress) {
                render(100, 'Completed', 'done');
                worker.stop();
                clearSoon();
            }
            return;
        }
        const pct = parseFloat(bar.style.width) || 0;
        const label = innerEl ? innerEl.innerText : '';
        sawProgress = true;

        if (/Encountered an error during download of|not found on CivitAI servers|requires a personal CivitAI API/.test(label)) {
            render(0, 'Download failed', 'failed');
            worker.stop();
            clearSoon();
            return;
        }
        if (pct >= 100) {
            render(100, 'Completed', 'done');
            worker.stop();
            clearSoon();
            return;
        }
        render(pct, label, 'active');
    }, 300);
}

function setDownloadProgressBar() {
    const gradio_html = gradioApp().querySelector('#queue_html_input textarea');

    // Sync the per-tab origin from the active queue item UP FRONT — before waiting for the
    // native bar to render. A previous Local download leaves body.civ-dl-origin-local set,
    // and the CSS hides #DownloadProgress while that class is present. If we waited for the
    // (hidden) bar first, we'd deadlock: the bar stays hidden because the origin is still
    // 'local', and the origin never flips to 'browser' because we never get past the wait.
    // Flipping it here re-shows the Browser bar the moment a Browser download starts.
    if (document.querySelector('#civitai_dl_list .civitai_dl_item')) {
        setCivDownloadOrigin(_currentDlOrigin());
    }

    let browserContainer = document.querySelector('#DownloadProgress');
    let browserProgress = browserContainer.querySelector('.progress-bar');
    if (!browserProgress || !browserProgress.style.width) {
        setTimeout(setDownloadProgressBar, 500);
        return;
    }

    let dlList = document.getElementById('civitai_dl_list');
    let nonQueue = dlList.querySelector('.civitai_nonqueue_list');
    let dlItem = dlList.querySelector('.civitai_dl_item');
    let dlBtn = dlItem.querySelector('.dl_action_btn > span');
    dlBtn.innerText = 'Cancel';
    dlBtn.setAttribute('onclick', 'cancelQueueDl()');
    let dlId = dlItem.getAttribute('dl_id');
    // The starting item's origin decides which tab shows progress (CSS body class).
    setCivDownloadOrigin(dlItem.getAttribute('dl_origin') || 'browser');
    let selector = '.civitai_dl_item[dl_id="' + parseInt(dlId) + '"]';

    let dlProgressBar = null;
    let percentage = null;
    let dlText = null;

    nonQueue.appendChild(dlItem);

    const worker = _createWorkerInterval(() => {
        browserContainer = document.querySelector('#DownloadProgress');
        if (!browserContainer) {
            return; // User switched tab, container not in DOM
        }
        browserProgress = browserContainer.querySelector('.progress-bar');
        dlText = browserContainer.querySelector('.progress-level-inner');
        if (!dlText || !browserProgress) {
            return;
        }
        dlText = dlText.innerText;
        percentage = parseFloat(browserProgress.style.width);

        dlItem = dlList.querySelector(selector);
        if (!dlItem) {
            return;
        }
        dlProgressBar = dlItem.querySelector('.dl_progress_bar');
        if (!dlProgressBar) {
            return;
        }

        dlProgressBar.textContent = percentage.toFixed(1) + '%';
        dlProgressBar.style.width = percentage + '%';

        if (percentage >= 100) {
            worker.stop();
            dlBtn = dlItem.querySelector('.dl_action_btn > span');
            dlBtn.innerText = 'Remove';
            dlBtn.setAttribute('onclick', 'removeDlItem(' + parseInt(dlId) + ', this)');
            dlItem.className = 'civitai_dl_item_completed';
            dlProgressBar.textContent = 'Completed';
            dlProgressBar.style.width = '100%';
            const gradio_input = ((document.querySelector('#civitai_dl_list.prose') || document.querySelector('#civitai_dl_list') || {}).innerHTML || '');
            gradio_html.value = gradio_input;
            updateInput(gradio_html);
            return;
        }

        if (currentDlCancelled) {
            worker.stop();
            dlBtn = dlItem.querySelector('.dl_action_btn > span');
            dlBtn.innerText = 'Remove';
            dlBtn.setAttribute('onclick', 'removeDlItem(' + parseInt(dlId) + ', this)');
            currentDlCancelled = false;
            dlItem.className = 'civitai_dl_item_failed';
            dlProgressBar.textContent = 'Cancelled';
            dlProgressBar.style.width = '0%';
            const gradio_input = ((document.querySelector('#civitai_dl_list.prose') || document.querySelector('#civitai_dl_list') || {}).innerHTML || '');
            gradio_html.value = gradio_input;
            updateInput(gradio_html);
            return;
        } else if (allDlCancelled) {
            worker.stop();
            allDlCancelled = false;
            let dlItems = dlList.querySelectorAll('.civitai_dl_item');
            dlItems.forEach(function (item) {
                dlBtn = dlItem.querySelector('.dl_action_btn > span');
                dlBtn.innerText = 'Remove';
                dlBtn.setAttribute('onclick', 'removeDlItem(' + parseInt(dlId) + ', this)');
                dlProgressBar = item.querySelector('.dl_progress_bar');
                dlProgressBar.textContent = 'Cancelled';
                dlProgressBar.style.width = '0%';
                nonQueue.appendChild(item);
                item.className = 'civitai_dl_item_failed';
            });
            const gradio_input = ((document.querySelector('#civitai_dl_list.prose') || document.querySelector('#civitai_dl_list') || {}).innerHTML || '');
            gradio_html.value = gradio_input;
            updateInput(gradio_html);
            return;
        } else if (dlText.includes('Encountered an error during download of') || dlText.includes('not found on CivitAI servers') || dlText.includes('requires a personal CivitAI API to be downloaded')) {
            worker.stop();
            dlBtn = dlItem.querySelector('.dl_action_btn > span');
            dlBtn.innerText = 'Remove';
            dlBtn.setAttribute('onclick', 'removeDlItem(' + parseInt(dlId) + ', this)');
            dlItem.className = 'civitai_dl_item_failed';
            dlProgressBar.textContent = 'Failed';
            dlProgressBar.style.width = '0%';
            const gradio_input = ((document.querySelector('#civitai_dl_list.prose') || document.querySelector('#civitai_dl_list') || {}).innerHTML || '');
            gradio_html.value = gradio_input;
            updateInput(gradio_html);
            return;
        }
    });
}

// === Queue Restore Banner ===

function initRestoreBanner(json) {
    const banner = gradioApp().querySelector('#restore_banner');
    if (!banner) return;
    if (!json || json.trim() === '') { banner.innerHTML = ''; return; }
    let items;
    try { items = JSON.parse(json); } catch (e) { return; }
    if (!items || items.length === 0) { banner.innerHTML = ''; return; }
    const count = items.length;
    const names = items.slice(0, 3).map(i => `<b>${i.model_name}</b>`).join(', ');
    const more = count > 3 ? ` and ${count - 3} more` : '';
    banner.innerHTML = `
        <div style="background:#1a3a5c;border:1px solid #2d6a9f;border-radius:8px;
                    padding:12px 16px;margin:8px 0;display:flex;align-items:center;
                    gap:12px;flex-wrap:wrap;">
            <span style="flex:1;min-width:200px;">
                🔄 <b>${count} download${count > 1 ? 's' : ''} need attention.</b> ${names}${more}
            </span>
            <button onclick="triggerRestoreQueue()"
                style="background:#2d6a9f;color:white;border:none;border-radius:6px;
                       padding:6px 14px;cursor:pointer;font-size:14px;">↺ Restore Queue</button>
            <button onclick="triggerDismissRestore()"
                style="background:transparent;color:#aaa;border:1px solid #555;
                       border-radius:6px;padding:6px 14px;cursor:pointer;font-size:14px;">✕ Dismiss</button>
        </div>`;
}

function triggerRestoreQueue() {
    const trigger = gradioApp().querySelector('#restore_action_trigger textarea');
    if (!trigger) return;
    trigger.value = String(Date.now());
    updateInput(trigger);
    const banner = gradioApp().querySelector('#restore_banner');
    if (banner) banner.innerHTML = '';
}

function triggerDismissRestore() {
    const trigger = gradioApp().querySelector('#dismiss_restore_trigger textarea');
    if (!trigger) return;
    trigger.value = '1';
    updateInput(trigger);
    const banner = gradioApp().querySelector('#restore_banner');
    if (banner) banner.innerHTML = '';
}

function removeDlItem(dl_id, element) {
    const gradio_html = gradioApp().querySelector('#queue_html_input textarea');
    const output = gradioApp().querySelector('#remove_dl_id textarea');
    var dl_item = element.parentNode.parentNode;
    dl_item.parentNode.removeChild(dl_item);
    output.value = dl_id;
    updateInput(output);

    const gradio_input = ((document.querySelector('#civitai_dl_list.prose') || document.querySelector('#civitai_dl_list') || {}).innerHTML || '');
    gradio_html.value = gradio_input;
    updateInput(gradio_html);
}

// Selects all models
// Browser-only checkboxes (exclude the Local Models grid so its selection is
// never toggled by the Browser's Select All / Download all selected actions).
function _browserCheckboxes() {
    return Array.from(document.querySelectorAll('.model-checkbox'))
        .filter((cb) => !cb.closest('#local_list_html'));
}

function selectAllModels() {
    const checkboxes = _browserCheckboxes();
    const allChecked = checkboxes.every((checkbox) => checkbox.checked);
    const allUnchecked = checkboxes.every((checkbox) => !checkbox.checked);
    if (allChecked || allUnchecked) {
        checkboxes.forEach(sendClick);
    } else {
        checkboxes.filter((checkbox) => !checkbox.checked).forEach(sendClick);
    }
}

// Deselects all models (Browser grid only)
function deselectAllModels() {
    setTimeout(() => {
        const checkboxes = _browserCheckboxes();
        checkboxes.filter((checkbox) => checkbox.checked).forEach(sendClick);
    }, 1000);
}

// Gradio's hidden textbox can lag a rapid sequence of checkbox input events. Capture
// the authoritative JS array in the SAME click that starts the batch, then forward
// that snapshot as the first Python input. This closes the race where four visible
// checks could arrive at selected_to_queue as an older two-item textbox value.
function prepareSelectedBrowserDownload(
    modelList,
    subfolder,
    downloadStart,
    createJson,
    currentHtml,
    baseFilter
) {
    const selectionSnapshot = JSON.stringify(selectedModels);
    deselectAllModels();
    return [
        selectionSnapshot,
        subfolder,
        downloadStart,
        createJson,
        currentHtml,
        baseFilter
    ];
}

// Sends Image URL to Python to pull generation info
function sendImgUrl(image_url) {
    const randomNumber = Math.floor(Math.random() * 1000);
    const genButton = gradioApp().querySelector('#txt2img_extra_tabs > div > button');
    const paddedNumber = String(randomNumber).padStart(3, '0');
    const input = gradioApp().querySelector('#civitai_text2img_input textarea');
    input.value = paddedNumber + '.' + image_url;
    updateInput(input);
    hideCivitaiOverlay();
    sendClick(genButton);
}

// "Send to txt2img" — build the infotext from the meta ALREADY rendered on the
// card (the same API meta shown to the user), instead of re-downloading the image
// and reading its embedded PNG-info (which CivitAI may strip/re-encode, so it can
// differ from what's shown). Falls back to the embedded-info path (sendImgUrl) only
// when this image has no meta rows on the card.
function sendToTxt2img(btn, image_url) {
    const block = btn.closest('.image-block');
    const rows = block ? block.querySelectorAll('[data-key]') : [];
    if (!rows || rows.length === 0) {
        sendImgUrl(image_url);
        return;
    }
    // CivitAI meta key -> A1111 infotext parameter label. Remaining keys (e.g.
    // "Denoising strength", "Hires upscale") are already A1111-style → passed as-is.
    const LABELS = {
        sampler: 'Sampler', steps: 'Steps', cfgScale: 'CFG scale',
        clipSkip: 'Clip skip', 'Clip skip': 'Clip skip', seed: 'Seed',
        Size: 'Size', Model: 'Model',
    };
    let positive = '';
    let negative = '';
    const params = [];
    rows.forEach(row => {
        const key = row.getAttribute('data-key');
        const dd = row.querySelector('dd');
        if (!key || !dd) return;
        const value = dd.textContent.trim();
        if (value === '') return;
        if (key === 'prompt') { positive = value; return; }
        if (key === 'negativePrompt') { negative = value; return; }
        params.push(`${LABELS[key] || key}: ${value}`);
    });
    if (!positive && !negative && params.length === 0) {
        sendImgUrl(image_url);
        return;
    }
    // Always emit the "Negative prompt:" line (even when empty): the WebUI's #paste
    // parser needs that structure to apply the prompt — a bare single-line positive
    // prompt is otherwise ignored (so a card with only a prompt sent nothing).
    let final = `${positive}\nNegative prompt: ${negative}`;
    if (params.length) final += `\n${params.join(', ')}`;
    const genButton = gradioApp().querySelector('#txt2img_extra_tabs > div > button');
    genInfo_to_txt2img(final, false);
    hideCivitaiOverlay();
    sendClick(genButton);
}

// Triggers a browser download for text content using a temporary Blob URL.
// Called by the export_csv_output / export_json_output change events.
function downloadBlobFile(content, filename, mimeType) {
    if (!content || !content.trim()) return;  // no data yet — ignore reset to ''
    const blob = new Blob([content], { type: mimeType });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    // Reset the hidden textbox so the next click fires a fresh change event
    const outputId = mimeType === 'text/csv' ? 'export_csv_output' : 'export_json_output';
    const box = gradioApp().querySelector(`#${outputId} textarea`);
    if (box) {
        const nativeSet = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
        nativeSet.call(box, '');
        box.dispatchEvent(new Event('input', { bubbles: true }));
    }
}

// Sends trained tags (trigger words) to txt2img prompt
// Shift+click appends to existing prompt; regular click replaces
function copyTriggerWord(text, btn) {
    navigator.clipboard.writeText(text).then(() => {
        const orig = btn.textContent;
        btn.textContent = '✓';
        setTimeout(() => { btn.textContent = orig; }, 1500);
    }).catch(() => {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand('copy'); } catch (_) {}
        document.body.removeChild(ta);
        const orig = btn.textContent;
        btn.textContent = '✓';
        setTimeout(() => { btn.textContent = orig; }, 1500);
    });
}

function sendTagsToPrompt(tags) {
    if (!tags || !tags.trim()) return;
    const genButton = gradioApp().querySelector('#txt2img_extra_tabs > div > button');
    const prompt = gradioApp().querySelector('#txt2img_prompt textarea');
    const neg_prompt = gradioApp().querySelector('#txt2img_neg_prompt textarea');
    const cfg_scale = gradioApp().querySelector('#txt2img_cfg_scale > div:nth-child(2) > div > input');
    if (!genButton || !prompt || !neg_prompt || !cfg_scale) return;
    const cfg = 'CFG scale: ' + cfg_scale.value + ', ';
    const prompt_addon = cfg + cfg + cfg;
    const cleanTags = tags.trimEnd().replace(/,\s*$/, '');
    const existing = (prompt.value || '').trimEnd().replace(/,\s*$/, '');
    const combined = existing ? existing + ', ' + cleanTags : cleanTags;
    const final = combined + '\nNegative prompt: ' + (neg_prompt.value || '') + '\n' + prompt_addon;
    genInfo_to_txt2img(final, false);
    sendClick(genButton);
    hideCivitaiOverlay();
}

// Sends txt2img info to txt2img tab
function genInfo_to_txt2img(genInfo, do_slice = true) {
    let insert = gradioApp().querySelector('#txt2img_prompt textarea');
    let pasteButton = gradioApp().querySelector('#paste');
    if (genInfo && insert && pasteButton) {
        insert.value = do_slice ? genInfo.slice(5) : genInfo;
        // updateInput notifies Gradio's frontend store that the value changed.
        updateInput(insert);
        // Defer the #paste click until Gradio has committed the new prompt value.
        // Clicking in the SAME tick intermittently makes #paste read a stale/empty
        // prompt, so it parses nothing and clears the field — the "giant infotext
        // appears, then the field empties" bug. Two animation frames reliably land
        // after the input->state sync. (.click() — not Event('click') — is required;
        // Gradio 4 ignores synthetic click events in some focus states.)
        requestAnimationFrame(() => requestAnimationFrame(() => pasteButton.click()));
    }
}

// Local Models pagination: write the target page to the hidden trigger so Python
// re-renders that slice of the (already sorted, in-memory) grid. The '.<rand>'
// suffix guarantees the Gradio change event fires even for a repeated page number.
function localGoToPage(page) {
    const trigger = gradioApp().querySelector('#local_page_trigger textarea');
    if (!trigger) return;
    trigger.value = String(page) + '.' + Math.floor(Math.random() * 1000);
    updateInput(trigger);
}

// Browser-only card filters. Gradio keeps Browser and Local Models mounted at the
// same time, and both grids use .civmodellist/.civmodelcard classes.
function _browserCardElements(selector) {
    return Array.from(document.querySelectorAll(selector))
        .filter((card) => !card.closest('#local_list_html'));
}

let _bannedCreators = [];
let _hideInstalledModels = false;
let _hideBannedCreatorsEnabled = false;

function _applyBrowserCardFilters() {
    _browserCardElements('.civmodelcard').forEach((card) => {
        const creator = card.getAttribute('data-creator');
        const hideForInstalled =
            _hideInstalledModels && card.classList.contains('civmodelcardinstalled');
        const hideForCreator =
            _hideBannedCreatorsEnabled && creator && _bannedCreators.includes(creator);
        card.style.display = (hideForInstalled || hideForCreator) ? 'none' : '';
    });
}

// Hide installed models in the Browser grid only.
function hideInstalled(toggleValue) {
    _hideInstalledModels = !!toggleValue;
    _applyBrowserCardFilters();
}

// === Creator Management (ban / favorite) ===
// Called when a new model list loads — sync banned list then apply filter
function initBannedCreators(listStr, checked) {
    _bannedCreators = listStr ? listStr.split(',').map(s => s.trim()).filter(Boolean) : [];
    hideBannedCreators(checked);
}

// Called after ban/fav button actions — refresh list and re-apply filter
function refreshBannedCreators(listStr, checked) {
    _bannedCreators = listStr ? listStr.split(',').map(s => s.trim()).filter(Boolean) : [];
    hideBannedCreators(checked);
}

// Show or hide cards of banned creators
function hideBannedCreators(checked) {
    _hideBannedCreatorsEnabled = !!checked;
    _applyBrowserCardFilters();
}

// Re-apply hideInstalled and banned-creator filters by reading current toggle states.
// Called from MutationObserver when new cards are injected into the DOM.
function reapplyFilters() {
    const hideInstalledToggle =
        gradioApp().querySelector('#toggle5 input[type="checkbox"]') ||
        gradioApp().querySelector('#toggle5L input[type="checkbox"]');
    if (hideInstalledToggle) {
        hideInstalled(hideInstalledToggle.checked);
    }

    const hideBannedToggle =
        gradioApp().querySelector('#hideBannedCreators input[type="checkbox"]');
    const bannedListInput =
        gradioApp().querySelector('#banned_creators_list');
    if (hideBannedToggle && bannedListInput) {
        refreshBannedCreators(bannedListInput.value, hideBannedToggle.checked);
    }

    filterLocalOutdated();
}

// Toggle description visibility
function toggleDescription(prefix = '') {
    const content = document.getElementById(prefix + 'description-content');
    const overlay = document.getElementById(prefix + 'description-overlay');
    const button = document.getElementById(prefix + 'description-toggle-btn');

    if (!content || !overlay || !button) return;

    const isExpanded = content.classList.contains('expanded');

    if (isExpanded) {
        // Collapse - animate back to 400px
        content.style.maxHeight = '400px';
        content.classList.remove('expanded');
        overlay.classList.remove('hidden');
        button.textContent = 'Show More';
    } else {
        // Expand - calculate full height and animate to it
        const scrollHeight = content.scrollHeight;
        content.style.maxHeight = scrollHeight + 'px';
        content.classList.add('expanded');
        overlay.classList.add('hidden');
        button.textContent = 'Show Less';
    }
}

// Initialize description toggle functionality
function initDescriptionToggle(prefix = '') {
    const content = document.getElementById(prefix + 'description-content');
    const overlay = document.getElementById(prefix + 'description-overlay');
    const button = document.getElementById(prefix + 'description-toggle-btn');

    if (!content || !overlay || !button) return;

    // Reset styles first
    content.style.maxHeight = '';
    content.classList.remove('expanded');
    overlay.classList.remove('hidden');
    button.classList.remove('hidden');

    // Check if content height exceeds 400px
    const scrollHeight = content.scrollHeight;

    // If content is less than or equal to 400px, hide toggle elements
    if (scrollHeight <= 400) {
        overlay.classList.add('hidden');
        button.classList.add('hidden');
        content.style.maxHeight = 'none';
    } else {
        // Set initial collapsed state
        content.style.maxHeight = '400px';
        button.textContent = 'Show More';
    }

    // Descriptions often embed <img> tags whose natural size isn't known yet
    // at this point, so scrollHeight above can be measured before the images
    // finish loading. Re-measure once each image settles so the toggle button
    // reflects the true content height instead of only working when images
    // happen to load from cache in time.
    const images = content.querySelectorAll('img');
    images.forEach(img => {
        if (img.complete) return;
        const recheck = () => {
            // Only relevant while still in the initial collapsed/hidden state -
            // don't fight the user if they've already expanded/collapsed it.
            if (content.classList.contains('expanded')) return;
            const newScrollHeight = content.scrollHeight;
            if (newScrollHeight <= 400) {
                overlay.classList.add('hidden');
                button.classList.add('hidden');
                content.style.maxHeight = 'none';
            } else {
                overlay.classList.remove('hidden');
                button.classList.remove('hidden');
                content.style.maxHeight = '400px';
            }
        };
        img.addEventListener('load', recheck, { once: true });
        img.addEventListener('error', recheck, { once: true });
    });
}

function submitNewSubfolder(subfolderId, subfolderValue) {
    const output = gradioApp().querySelector('#create_subfolder textarea');
    output.value = subfolderId + '.add.' + subfolderValue;
    updateInput(output);
}

function deleteSubfolder(subfolderId) {
    const output = gradioApp().querySelector('#create_subfolder textarea');
    output.value = subfolderId + '.delete.';
    updateInput(output);
}

function createCustomSubfolder(subfolderDiv, subfolderId, subfolderValue) {
    if (typeof subfolderId === 'undefined') {
        console.error('subfolderId is required.');
        return;
    }

    const newContainerDiv = document.createElement('div');
    newContainerDiv.classList.add('svelte-1f354aw', 'container', 'CivitDefaultSubfolder');
    newContainerDiv.style.display = 'flex';
    newContainerDiv.style.alignItems = 'center';

    newContainerDiv.setAttribute('subfolder_id', subfolderId);

    const newTextArea = document.createElement('textarea');
    newTextArea.setAttribute('data-testid', 'textbox');
    newTextArea.classList.add('scroll-hide', 'svelte-1f354aw');
    newTextArea.setAttribute('dir', 'ltr');
    newTextArea.setAttribute('placeholder', '{BASEMODEL}/{NSFW}/{AUTHOR}/{MODELNAME}/{MODELID}/{VERSIONNAME}/{VERSIONID}');
    newTextArea.setAttribute('rows', '1');
    newTextArea.style.overflowY = 'scroll';
    newTextArea.style.height = '42px';
    newTextArea.style.flex = '1';

    if (typeof subfolderValue !== 'undefined') {
        newTextArea.value = subfolderValue;
    }

    newTextArea.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            submitNewSubfolder(subfolderId, newTextArea.value);
        }
    });

    const saveButton = document.createElement('button');
    saveButton.textContent = 'Save';
    saveButton.classList.add('save-button', 'lg', 'primary', 'gradio-button', 'svelte-cmf5ev');
    saveButton.setAttribute('title', '');
    saveButton.style.marginRight = '10px';
    saveButton.addEventListener('click', function () {
        submitNewSubfolder(subfolderId, newTextArea.value);
    });

    const deleteButton = document.createElement('button');
    deleteButton.textContent = 'Delete';
    deleteButton.classList.add('delete-button', 'lg', 'primary', 'gradio-button', 'svelte-cmf5ev');
    deleteButton.style.marginRight = '10px';
    deleteButton.addEventListener('click', function () {
        deleteSubfolder(subfolderId);
        newContainerDiv.remove();
    });

    newContainerDiv.appendChild(deleteButton);
    newContainerDiv.appendChild(saveButton);
    newContainerDiv.appendChild(newTextArea);

    subfolderDiv.appendChild(newContainerDiv);
}

function insertExistingSubfolders(input) {
    const subfolder = document.querySelectorAll('civitai-custom-subfolder-div');
    createCustomSubfolder(subfolder, Id, Value);
}

function createSubfolderButton() {
    const subfolderParent = document.getElementById('create-sub-accordion');
    const subfolderDiv = subfolderParent.querySelector('.accordion');

    const subfolder = document.createElement('div');
    subfolder.classList.add('flex-column-layout', 'civitai-custom-subfolder-div');

    const customSubfoldersList = document.querySelector('#custom_subfolders_list');
    const textarea = customSubfoldersList.querySelector('textarea');
    const subfoldersString = textarea ? textarea.value : '';

    const subfoldersArray = subfoldersString.split('␞␞');

    for (let i = 0; i < subfoldersArray.length; i += 2) {
        const subfolderId = subfoldersArray[i];
        const subfolderValue = subfoldersArray[i + 1];

        createCustomSubfolder(subfolder, subfolderId, subfolderValue);
    }

    const buttonContainer = document.createElement('div');
    buttonContainer.classList.add('sub-folder-button-container');
    buttonContainer.style.display = 'flex';
    buttonContainer.style.gap = '10px';

    const optionsDiv = document.createElement('div');
    optionsDiv.classList.add('placeholder-options-container');
    optionsDiv.style.display = 'flex';
    optionsDiv.style.justifyContent = 'center';

    const plusButton = document.createElement('button');
    plusButton.textContent = 'Create new default sub folder entry';
    plusButton.classList.add('plus-button', 'lg', 'primary', 'gradio-button', 'svelte-cmf5ev');
    plusButton.style.marginTop = '10px';
    plusButton.addEventListener('click', function () {
        const existingSubfolderDivs = document.querySelectorAll('div.CivitDefaultSubfolder');
        let highestSubfolderId = 0;

        existingSubfolderDivs.forEach((div) => {
            const subfolderId = parseInt(div.getAttribute('subfolder_id'), 10);
            if (subfolderId > highestSubfolderId) {
                highestSubfolderId = subfolderId;
            }
        });

        const newSubfolderId = highestSubfolderId + 1;
        createCustomSubfolder(subfolder, newSubfolderId);
    });

    // Create the guide button
    const guide_html = `
    <div style="text-align: center;">
        <div>These options can be used to add sub-folder options.</div>
        <div>There are a few placeholders you can use which will be automatically replaced with the selected model's information:</div>
        <div>‎</div>
        <div>{BASEMODEL}: Replaced with the base model name.</div>
        <div>{NSFW}: Creates a folder named "nsfw", folder will not be created if model is sfw.</div>
        <div>{AUTHOR}: Replaced with the author of the model.</div>
        <div>{MODELNAME}: Replaced with the name of the model.</div>
        <div>{MODELID}: Replaced with the unique ID of the model.</div>
        <div>{VERSIONNAME}: Replaced with the version name of the model.</div>
        <div>{VERSIONID}: Replaced with the unique ID of the model version.</div>
        <div>‎</div>
        <div>For example, if I select a model called 'ReV Animated'</div>
        <div>and it's version is called 'V2 Rebirth' then the following:</div>
        <div>{MODELNAME}/{VERSIONNAME}</div>
        <div>Will be replaced with:</div>
        <div>ReV Animated/V2 Rebirth</div>
        <div>‎</div>
        <div>Always use '/' as a seperator, regardless of your OS</div>
    </div>
    `;
    const guideButton = document.createElement('button');
    guideButton.textContent = 'Guide';
    guideButton.classList.add('guide-button', 'lg', 'primary', 'gradio-button', 'svelte-cmf5ev');
    guideButton.style.marginTop = '10px';
    guideButton.addEventListener('click', function () {
        modelInfoPopUp(null, null, true);
        insertGuideMessage(guide_html);
    });

    const optionsText = document.createElement('span');
    optionsText.textContent = 'Available options: {BASEMODEL} {NSFW} {AUTHOR} {MODELNAME} {MODELID} {VERSIONNAME} {VERSIONID}';

    // Append buttons to the container
    buttonContainer.appendChild(guideButton);
    buttonContainer.appendChild(plusButton);

    optionsDiv.appendChild(optionsText);

    subfolder.insertBefore(optionsDiv, subfolder.firstChild);
    subfolder.insertBefore(buttonContainer, subfolder.firstChild);
    subfolderDiv.appendChild(subfolder);
}

function insertGuideMessage(html_input) {
    const overlayContainer = document.querySelector('.civitai-overlay-inner');
    if (overlayContainer) {
        const guideHtml = document.createElement('div');
        guideHtml.innerHTML = html_input;
        while (guideHtml.firstChild) {
            overlayContainer.appendChild(guideHtml.firstChild);
        }
    }
}

// === ANXETY EDITs ===
// Runs all functions when the page is fully loaded
function onPageLoad() {
    updateSVGIcons();

    let subfolderDiv = document.querySelector('#settings_civitai_browser_plus > div > div');
    let downloadDiv = document.querySelector('#settings_civitai_browser_download > div > div');
    let settingsDiv = document.querySelector('#settings_civitai_browser > div > div');

    if (subfolderDiv || downloadDiv) {
        let div = subfolderDiv || downloadDiv;
        let subfolders = div.querySelectorAll("[id$='subfolder']");
        createAccordion(div, subfolders, 'Default sub folders', 'default-sub-accordion');
        createAccordion(div, null, 'Create sub folder entries', 'create-sub-accordion');
        createSubfolderButton();
    }

    if (subfolderDiv || settingsDiv) {
        let div = subfolderDiv || settingsDiv;
        let proxy = div.querySelectorAll("[id$='proxy']");
        createAccordion(div, proxy, 'Proxy options', 'proxy-accordion');
    }

    let toggle4L = document.getElementById('toggle4L');
    let toggle4 = document.getElementById('toggle4');
    let hash_toggle_hover = document.querySelector('#skip_hash_toggle > label');
    let hash_toggle = document.querySelector('#skip_hash_toggle');
    let do_html_gen_hover = document.querySelector('#do_html_gen > label');
    let do_html_gen = document.querySelector('#do_html_gen');

    if (toggle4L || toggle4) {
        let like_toggle = toggle4L || toggle4;
        let insertText = 'Requires an API Key\nConfigurable in CivitAI settings tab';
        createTooltip(like_toggle, like_toggle, insertText);
    }

    if (hash_toggle) {
        let insertText =
            'This option generates unique hashes for models that were not downloaded with this extension.\nA hash is required for any of the options below to work, a model with no hash will be skipped.\nInitial hash generation is a one-time process per file.';
        createTooltip(hash_toggle, hash_toggle_hover, insertText);
    }

    if (do_html_gen) {
        let insertText =
            'This option requires the "Save HTML file when saving model" option to be enabled.\nYou can find this setting in the CivitAI Browser+ settings under Downloads section.';
        createTooltip(do_html_gen, do_html_gen_hover, insertText);
    }

    addOnClickToButtons();
    initNativeCardTheme();
    createCivitAICardButtons();
    adjustFilterBoxAndButtons();
    setupClickOutsideListener();
    watchNativeBadgeData();
    requestNativeBadgeData();
    initNativeCardObserver();
}

// Cards aren't only added at page-load/refresh-click time — Gradio lazily re-renders the
// Extra Networks grid on tab switches, checkpoint changes, and scroll, and none of those
// go through addOnClickToButtons's listeners. Without this, buttons/badges only appear
// after the user manually clicks the native refresh button. Debounced since grid updates
// can fire many mutations in a row; re-running createCivitAICardButtons() is safe/idempotent
// since every insertion point already checks whether its element exists first.
let _nativeCardObserverTimer = null;
function initNativeCardObserver() {
    const app = gradioApp();
    if (!app || app.__civitaiCardObserverAttached) return;
    app.__civitaiCardObserverAttached = true;

    const observer = new MutationObserver((mutations) => {
        const hasNewCard = mutations.some((m) =>
            Array.from(m.addedNodes).some((node) =>
                node.nodeType === 1 && (node.matches?.('.card') || node.querySelector?.('.card'))
            )
        );
        if (!hasNewCard) return;

        clearTimeout(_nativeCardObserverTimer);
        _nativeCardObserverTimer = setTimeout(() => {
            createCivitAICardButtons();
        }, 250);
    });

    observer.observe(app, { childList: true, subtree: true });
}

// The Settings tab's checkbox may not be mounted yet at onUiLoaded time, so poll briefly
// (matches the existing checkSettingsLoad pattern) instead of silently no-op'ing.
function initNativeCardTheme() {
    let attempts = 0;
    const tryInit = setInterval(() => {
        attempts++;
        const checkbox = gradioApp().querySelector('#setting_civitai_native_card_theme input[type=checkbox]');
        if (checkbox) {
            clearInterval(tryInit);
            syncNativeCardThemeSetting();
        } else if (attempts > 25) {
            clearInterval(tryInit);
        }
    }, 200);
}

// Watches the hidden #native_badge_data output textarea for the JSON blob written by
// civitai_file_manage.get_native_card_badge_json, and re-applies badges once it lands.
function watchNativeBadgeData() {
    const output = gradioApp().querySelector('#native_badge_data textarea');
    if (!output) return;

    const parseAndApply = () => {
        try {
            window.__civitaiNativeBadges = JSON.parse(output.value || '{}');
        } catch (e) {
            window.__civitaiNativeBadges = {};
        }
        createCivitAICardButtons();
    };

    const observer = new MutationObserver(parseAndApply);
    observer.observe(output, { attributes: true, childList: true, characterData: true, subtree: true });
    output.addEventListener('input', parseAndApply);
}

onUiLoaded(onPageLoad);

function checkSettingsLoad() {
    const divElement = gradioApp().querySelector('#setting_custom_api_key');
    const infoElement = divElement?.querySelector('.info');
    if (!infoElement) {
        return;
    }
    clearInterval(settingsLoadInterval);
    createLink(infoElement);
}
let settingsLoadInterval = setInterval(checkSettingsLoad, 1000);

// === Simple Image Viewer ===
// Global viewer state
let currentViewerOverlay = null;
let viewerEventListeners = [];

// Create viewer overlay dynamically
function createViewerOverlay() {
    // Remove existing viewer if it exists
    const existingViewer = document.getElementById('image-viewer-overlay');
    if (existingViewer) {
        existingViewer.remove();
    }

    // Create new viewer overlay
    const overlay = document.createElement('div');
    overlay.id = 'image-viewer-overlay';
    overlay.className = 'viewer-overlay';

    const content = document.createElement('div');
    content.className = 'viewer-content';

    const image = document.createElement('img');
    image.id = 'viewer-image';
    image.className = 'viewer-media';
    image.alt = '';

    const video = document.createElement('video');
    video.id = 'viewer-video';
    video.className = 'viewer-media';
    video.controls = true;
    video.muted = true;
    video.style.display = 'none';

    const source = document.createElement('source');
    source.type = 'video/mp4';
    video.appendChild(source);

    content.appendChild(image);
    content.appendChild(video);
    overlay.appendChild(content);

    // Add to body
    document.body.appendChild(overlay);

    return overlay;
}

// Open image viewer overlay
function openImageViewer(mediaUrl, mediaType) {
    // Create or get viewer overlay
    let overlay = document.getElementById('image-viewer-overlay');
    if (!overlay) {
        overlay = createViewerOverlay();
    }

    const viewerImage = document.getElementById('viewer-image');
    const viewerVideo = document.getElementById('viewer-video');

    if (!overlay || !viewerImage || !viewerVideo) return;

    // Setup media element
    if (mediaType === 'video') {
        viewerImage.style.display = 'none';
        viewerVideo.style.display = 'block';
        const source = viewerVideo.querySelector('source');
        if (source) {
            source.src = mediaUrl;
            viewerVideo.load();
        }
    } else {
        viewerVideo.style.display = 'none';
        viewerImage.style.display = 'block';
        viewerImage.src = mediaUrl;
    }

    // Position overlay to cover entire viewport with proper centering
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100vw';
    overlay.style.height = '100vh';
    overlay.style.zIndex = '99999';
    overlay.style.display = 'flex';
    overlay.style.alignItems = 'center';
    overlay.style.justifyContent = 'center';

    // Show overlay with animation
    overlay.style.display = 'flex';
    overlay.classList.remove('closing');
    requestAnimationFrame(() => {
        overlay.classList.add('active');
    });

    // Prevent body scroll
    document.body.style.overflow = 'hidden';

    // Setup event listeners
    setupViewerEventListeners(overlay);

    currentViewerOverlay = overlay;
}

// Setup event listeners for viewer
function setupViewerEventListeners(overlay) {
    // Remove existing listeners
    cleanupViewerEventListeners();

    const viewerImage = document.getElementById('viewer-image');
    const viewerVideo = document.getElementById('viewer-video');

    // Keyboard handler
    const keyHandler = (e) => {
        if (e.key === 'Escape') {
            closeImageViewer();
            e.stopPropagation();
            e.preventDefault();
        }
    };

    // Overlay click handler
    const overlayHandler = (e) => {
        if (e.target.classList.contains('viewer-overlay') || e.target.classList.contains('viewer-content')) {
            closeImageViewer();
        }
    };

    // Media click handler
    const mediaHandler = (e) => {
        e.stopPropagation();
    };

    // Add listeners
    document.addEventListener('keydown', keyHandler);
    overlay.addEventListener('click', overlayHandler);
    if (viewerImage) viewerImage.addEventListener('click', mediaHandler);
    if (viewerVideo) viewerVideo.addEventListener('click', mediaHandler);

    // Store references for cleanup
    viewerEventListeners = [
        {element: document, event: 'keydown', handler: keyHandler},
        {element: overlay, event: 'click', handler: overlayHandler},
        {element: viewerImage, event: 'click', handler: mediaHandler},
        {element: viewerVideo, event: 'click', handler: mediaHandler},
    ];
}

// Cleanup event listeners
function cleanupViewerEventListeners() {
    viewerEventListeners.forEach(({element, event, handler}) => {
        if (element && handler) {
            element.removeEventListener(event, handler);
        }
    });
    viewerEventListeners = [];
}

// Close image viewer overlay
function closeImageViewer() {
    const overlay = document.getElementById('image-viewer-overlay');
    if (!overlay || !overlay.classList.contains('active')) return;

    // Add closing animation
    overlay.classList.add('closing');
    overlay.classList.remove('active');

    setTimeout(() => {
        overlay.style.display = 'none';
        overlay.classList.remove('closing');

        // Restore body scroll only if civitai overlay is not open
        if (!document.querySelector('.civitai-overlay')) {
            document.body.style.overflow = 'auto';
        }

        // Cleanup event listeners
        cleanupViewerEventListeners();

        currentViewerOverlay = null;
    }, 300);
}

// Global flag to track if viewer is initialized
let viewerInitialized = false;
let previewMediaObserver = null;

// Handle click on preview media - lazy initialization
function handlePreviewMediaClick(e) {
    e.preventDefault();
    e.stopPropagation();

    // Initialize viewer on first click if not already done
    if (!viewerInitialized) {
        initializeImageViewer();
        viewerInitialized = true;
    }

    const element = e.target;
    const isVideo = element.tagName.toLowerCase() === 'video';
    const mediaUrl = isVideo ? element.querySelector('source')?.src || element.src : element.src;

    if (mediaUrl) {
        openImageViewer(mediaUrl, isVideo ? 'video' : 'image');
    }
}

// Initialize image viewer for preview media elements (lazy initialization)
function initializeImageViewer() {
    // Add click handlers to existing preview media elements
    const previewMediaElements = document.querySelectorAll('.preview-media');
    previewMediaElements.forEach((element) => {
        element.addEventListener('click', handlePreviewMediaClick);
    });

    // Set up MutationObserver for dynamically added elements
    if (!previewMediaObserver) {
        previewMediaObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // Check if the added node is a preview media element
                        if (node.classList && node.classList.contains('preview-media')) {
                            node.addEventListener('click', handlePreviewMediaClick);
                        }
                        // Check for preview media elements within the added node
                        const previewElements = node.querySelectorAll && node.querySelectorAll('.preview-media');
                        if (previewElements) {
                            previewElements.forEach((element) => {
                                element.addEventListener('click', handlePreviewMediaClick);
                            });
                        }
                    }
                });
            });
        });

        // Start observing
        previewMediaObserver.observe(document.body, {
            childList: true,
            subtree: true,
        });
    }
}

// Delete installed model with confirmation
function deleteInstalledModel(event, modelString, sha256, installedCount = 1) {
    // Stop event propagation to prevent card selection
    event.stopPropagation();
    event.preventDefault();

    const installedTotal = Number(installedCount || 0);
    if (installedTotal > 1) {
        select_model(modelString, null);
        alert(
            `This model has ${installedTotal} installed versions.\n\n` +
            'For safety, quick delete is disabled.\n' +
            'Please choose the exact [Installed] version in the Browser panel and use "Delete model" there.'
        );
        return;
    }
    
    if (!sha256) {
        alert('Error: No SHA256 hash available for this model. Cannot delete.');
        return;
    }
    
    // Strip the trailing " (id)" part for display only
    const displayName = modelString.replace(/\s*\(\d+\)\s*$/, '');
    
    // Show confirmation dialog
    const confirmMessage = `Are you sure you want to delete "${displayName}"?\n\nThis will move the model and its associated files to the trash.`;
    if (!confirm(confirmMessage)) {
        return;
    }
    
    // Find the delete trigger input element (presence check — ensures UI is loaded)
    const deleteFinishInput = gradioApp().querySelector('#delete_finish textarea');
    if (!deleteFinishInput) {
        alert('Error: Delete function not available.');
        console.error('Could not find #delete_finish element');
        return;
    }
    
    // Find the SHA256 input element
    const sha256Input = gradioApp().querySelector('#sha256 textarea');
    if (!sha256Input) {
        alert('Error: SHA256 input not found.');
        console.error('Could not find #sha256 element');
        return;
    }
    
    // Set SHA256 value and let Gradio's reactive store register it before we click.
    sha256Input.value = sha256;
    updateInput(sha256Input);

    const triggerDelete = () => {
        const deleteButton = gradioApp().querySelector('#delete_trigger_btn');
        if (!deleteButton) {
            console.error('Could not find #delete_trigger_btn element');
            alert('Error: Delete button not found. Please try using the delete button in the model details panel.');
            return;
        }
        deleteButton.click();
        // After deletion completes, update the card visually (remove installed state).
        // Skip pressRefresh() fallback to avoid expensive full-page API re-fetch.
        setTimeout(() => updateCard(modelString + '.None', false), 500);
    };

    // Two animation frames guarantee the 'input' event has propagated into Gradio's
    // store, so the backend reads the SHA256 we just set — not a stale/empty value.
    // (Replaces a fixed 100ms timeout that could fire before propagation under load.)
    requestAnimationFrame(() => requestAnimationFrame(triggerDelete));
}


// ── Update Mode ──────────────────────────────────────────────────────────────

/**
 * Trigger the Python backend to enqueue ALL models from gl.update_items.
 * Called by the "⬆️ Update All" button in the update mode action bar.
 */
function updateAllModels() {
    const trigger = gradioApp().querySelector('#update_all_trigger textarea');
    if (!trigger) return;
    setCivDownloadOrigin('local');
    trigger.value = String(Date.now());
    updateInput(trigger);
}

/**
 * Called by the "Update All / Update Selected" button.
 * If any update-grid checkboxes are checked, updates only those; otherwise updates all.
 */
function updateOrSelectedModels() {
    if (selectedModels.length > 0) {
        const trigger = gradioApp().querySelector('#update_selected_trigger textarea');
        if (!trigger) return;
        setCivDownloadOrigin('local');
        trigger.value = JSON.stringify(selectedModels);
        updateInput(trigger);
        // Visual feedback: dim checked cards
        gradioApp().querySelectorAll('.model-checkbox:checked').forEach(cb => {
            const card = cb.closest('.civmodelcard');
            if (card) card.style.opacity = '0.4';
        });
    } else {
        updateAllModels();
    }
}

/**
 * Syncs the Update All/Selected button label with the current selection count.
 */
function syncUpdateBtn() {
    const btn = gradioApp().querySelector('#civupdate-update-btn');
    if (!btn) return;
    const n     = selectedModels.length;
    const total = _browserCheckboxes().length;
    btn.textContent = n > 0
        ? `\u2b06\ufe0f Update Selected (${n})`
        : `\u2b06\ufe0f Update All (${total})`;
}

/**
 * Trigger the Python backend to enqueue a SINGLE model update.
 * Called by the ⬆ button on an individual update card.
 * Collects checked version IDs from the card's version checkboxes.
 * @param {string|number} modelId  - the CivitAI model id
 * @param {string}        family   - the installed family (e.g. 'PONY', 'IL', '')
 */
function updateSingleModel(modelId, family) {
    const card = gradioApp().querySelector(
        `.update-mode-card[data-model-id="${modelId}"][data-family="${(family || '').toUpperCase()}"]`
    );

    let checkedVersions = [];
    if (card) {
        checkedVersions = Array.from(
            card.querySelectorAll('.ver-checkbox:checked')
        ).map(cb => parseInt(cb.dataset.verId, 10));
    }

    const trigger = gradioApp().querySelector('#update_single_trigger textarea');
    if (!trigger) return;

    // Format: model_id|family|json_array_of_ver_ids
    // If no versions checked, sends empty array → Python falls back to auto-resolution
    trigger.value = `${modelId}|${family || ''}|${JSON.stringify(checkedVersions)}`;
    updateInput(trigger);

    // Visual feedback: dim the card
    if (card) card.style.opacity = '0.4';
}

/**
 * Exit Update Mode: clear the banner and tell Python to reset the page state.
 */
function exitUpdateMode() {
    const trigger = gradioApp().querySelector('#exit_update_mode_trigger textarea');
    if (!trigger) return;
    trigger.value = String(Date.now());
    updateInput(trigger);
    // Immediately clear the banner
    const banner = gradioApp().querySelector('#update_mode_banner');
    if (banner) banner.innerHTML = '';
}
/**
 * Trigger the Python backend to mark a local model file for review.
 * Called by the "Mark for review" button injected into the overlay HTML.
 * @param {string} filePath - absolute path to the local model file
 */
function markForReviewOverlay(filePath) {
    const trigger = gradioApp().querySelector('#mark_review_overlay_trigger textarea');
    if (!trigger) return;
    trigger.value = filePath;
    updateInput(trigger);
}

// ── LoraDex ──────────────────────────────────────────────────────────────────

function _loradexSetCommand(payload) {
    const input = gradioApp().querySelector('#loradex_command_state textarea');
    if (!input) {
        console.error('[LoraDex] command state input not found');
        return;
    }
    input.value = JSON.stringify(payload);
    updateInput(input);
}

function loradexMarkPending(select) {
    const row = select.closest('.loradex-row');
    const saved = select.dataset.saved;
    const current = select.value;
    if (current !== saved) {
        row.classList.add('loradex-pending');
    } else {
        row.classList.remove('loradex-pending');
    }
    loradexSyncActionButtons();
}

function loradexSyncActionButtons() {
    const pendingRows = document.querySelectorAll('.loradex-pending');
    const anyPending = pendingRows.length > 0;
    const applyBtn = gradioApp().querySelector('#loradex_apply_all_btn');
    const resetBtn = gradioApp().querySelector('#loradex_reset_all_btn');
    if (applyBtn) applyBtn.disabled = !anyPending;
    if (resetBtn) resetBtn.disabled = !anyPending;
}

function loradexApplyLine(btnOrPath) {
    const filePath = typeof btnOrPath === 'string' ? btnOrPath : btnOrPath.closest('.loradex-row')?.dataset?.filepath;
    if (!filePath) return;
    const row = document.querySelector(`.loradex-row[data-filepath="${CSS.escape(filePath)}"]`);
    if (!row) return;
    const select = row.querySelector('.loradex-cat');
    if (!select) return;
    _loradexSetCommand({
        command: 'apply',
        data: { file_path: filePath, category: select.value }
    });
}

function loradexResetLine(btnOrPath) {
    const filePath = typeof btnOrPath === 'string' ? btnOrPath : btnOrPath.closest('.loradex-row')?.dataset?.filepath;
    if (!filePath) return;
    const row = document.querySelector(`.loradex-row[data-filepath="${CSS.escape(filePath)}"]`);
    if (!row) return;
    const select = row.querySelector('.loradex-cat');
    if (!select) return;
    select.value = select.dataset.saved;
    row.classList.remove('loradex-pending');
    _loradexSetCommand({
        command: 'reset',
        data: { file_path: filePath }
    });
    loradexSyncActionButtons();
}

function loradexApplyAll() {
    const rows = document.querySelectorAll('.loradex-pending');
    const pending = [];
    rows.forEach(row => {
        const select = row.querySelector('.loradex-cat');
        if (select) {
            pending.push({ file_path: select.dataset.filepath, category: select.value });
        }
    });
    if (!pending.length) return;
    _loradexSetCommand({ command: 'apply-all', data: pending });
}

function loradexResetAll() {
    const rows = document.querySelectorAll('.loradex-pending');
    const pendingPaths = [];
    rows.forEach(row => {
        const select = row.querySelector('.loradex-cat');
        if (select) {
            select.value = select.dataset.saved;
            row.classList.remove('loradex-pending');
            pendingPaths.push(select.dataset.filepath);
        }
    });
    _loradexSetCommand({ command: 'reset-all', data: pendingPaths });
    loradexSyncActionButtons();
}

// ── LoraDex bulk selection ───────────────────────────────────────────────────
// Selection is page-local by design: it lives in the DOM and every re-render
// (paging, filtering, applying) clears it, so a click can never reach a row the
// user is no longer looking at.

function loradexSyncSelection() {
    const checked = document.querySelectorAll('.loradex-check:checked');
    const count = checked.length;

    const label = document.querySelector('.loradex-selection-count');
    if (label) label.textContent = `${count} selected`;

    const applyBtn = document.querySelector('.loradex-bulk-apply');
    if (applyBtn) applyBtn.disabled = count === 0;

    // Keep the header checkbox honest about a partial selection.
    const all = document.querySelectorAll('.loradex-check');
    const checkAll = document.querySelector('.loradex-check-all');
    if (checkAll) {
        checkAll.checked = count > 0 && count === all.length;
        checkAll.indeterminate = count > 0 && count < all.length;
    }
}

function loradexSelectAllPage(source) {
    document.querySelectorAll('.loradex-check').forEach(box => {
        box.checked = source.checked;
    });
    loradexSyncSelection();
}

function loradexApplySelected() {
    const filePaths = [];
    document.querySelectorAll('.loradex-check:checked').forEach(box => {
        filePaths.push(box.dataset.filepath);
    });
    if (!filePaths.length) return;

    const select = document.querySelector('.loradex-bulk-cat');
    if (!select) return;

    _loradexSetCommand({
        command: 'apply-selected',
        data: { file_paths: filePaths, category: select.value }
    });
}

function loradexGoToPage(n) {
    const trigger = gradioApp().querySelector('#loradex_page_trigger textarea');
    if (!trigger) return;
    trigger.value = String(n) + '.' + String(Date.now()).slice(-3);
    updateInput(trigger);
}

let _loradexZoomEl = null;
function loradexHoverZoom(event, imgSrc) {
    if (_loradexZoomEl) return;
    const zoom = document.createElement('div');
    zoom.className = 'loradex-zoom-preview';
    zoom.style.backgroundImage = `url("${imgSrc}")`;
    document.body.appendChild(zoom);
    _loradexZoomEl = zoom;
    loradexMoveZoom(event);
    document.addEventListener('mousemove', loradexMoveZoom);
}

function loradexMoveZoom(event) {
    if (!_loradexZoomEl) return;
    const x = event.clientX + 20;
    const y = event.clientY + 20;
    _loradexZoomEl.style.left = x + 'px';
    _loradexZoomEl.style.top = y + 'px';
}

function loradexHideZoom() {
    if (!_loradexZoomEl) return;
    document.removeEventListener('mousemove', loradexMoveZoom);
    _loradexZoomEl.remove();
    _loradexZoomEl = null;
}
