(function() {
    'use strict';
    
    // Configuration
    const CONFIG = {
        animationSpeed: 1.5,
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        backdropBlur: '8px',
        primaryColor: '#4f46e5',
        secondaryColor: '#8b5cf6',
        showProgress: true,
        autoHide: true,
        hideDelay: 300, 
        zIndex: 999999,
        enableLinkInterception: true,
        enableAjaxInterception: false,
        message: 'Loading...',
        showPercentage: true,
        customStyles: {}
    };
    
    let isLoading = false;
    let loadProgress = 0;
    let progressInterval = null;
    let simulatedProgress = false;
    
    function createLoader() {
        // Remove existing loader if any
        const existingLoader = document.getElementById('modernLoadingIndicator');
        if (existingLoader) existingLoader.remove();
        
        // Create loader container
        const loaderContainer = document.createElement('div');
        loaderContainer.id = 'modernLoadingIndicator';
        
        Object.assign(loaderContainer.style, {
            position: 'fixed',
            top: '0',
            left: '0',
            width: '100%',
            height: '100%',
            background: CONFIG.backgroundColor,
            backdropFilter: `blur(${CONFIG.backdropBlur})`,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: CONFIG.zIndex,
            opacity: '0',
            transition: 'opacity 0.3s ease',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, sans-serif',
            pointerEvents: 'none'
        });
        
        Object.assign(loaderContainer.style, CONFIG.customStyles);
        
        // Create loader animation
        const loaderAnimation = document.createElement('div');
        loaderAnimation.className = 'loader-animation';
        loaderAnimation.style.cssText = `
            width: 80px;
            height: 80px;
            position: relative;
            margin-bottom: 30px;
        `;
        
        // Create spinner circles
        for (let i = 0; i < 3; i++) {
            const circle = document.createElement('div');
            circle.className = `loader-circle circle-${i + 1}`;
            circle.style.cssText = `
                position: absolute;
                width: 100%;
                height: 100%;
                border: 3px solid transparent;
                border-top-color: ${i === 0 ? CONFIG.primaryColor : i === 1 ? CONFIG.secondaryColor : '#a78bfa'};
                border-radius: 50%;
                animation: spin ${CONFIG.animationSpeed * (i + 1) / 2}s linear infinite;
                opacity: ${0.8 - (i * 0.2)};
            `;
            loaderAnimation.appendChild(circle);
        }
        
        // Create center dot
        const centerDot = document.createElement('div');
        centerDot.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 16px;
            height: 16px;
            background: ${CONFIG.primaryColor};
            border-radius: 50%;
            box-shadow: 0 0 20px ${CONFIG.primaryColor};
        `;
        loaderAnimation.appendChild(centerDot);
        
        // Create progress container
        const progressContainer = document.createElement('div');
        progressContainer.className = 'loader-progress';
        progressContainer.style.cssText = `
            width: 200px;
            margin-top: 20px;
            display: ${CONFIG.showProgress ? 'block' : 'none'};
        `;
        
        // Create progress bar
        const progressBar = document.createElement('div');
        progressBar.className = 'progress-bar';
        progressBar.style.cssText = `
            width: 100%;
            height: 4px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 2px;
            overflow: hidden;
            margin-bottom: 10px;
        `;
        
        const progressFill = document.createElement('div');
        progressFill.id = 'loaderProgressFill';
        progressFill.style.cssText = `
            width: 0%;
            height: 100%;
            background: linear-gradient(90deg, ${CONFIG.primaryColor}, ${CONFIG.secondaryColor});
            border-radius: 2px;
            transition: width 0.3s ease;
        `;
        
        progressBar.appendChild(progressFill);
        progressContainer.appendChild(progressBar);
        
        // Create progress text
        const progressText = document.createElement('div');
        progressText.id = 'loaderProgressText';
        progressText.style.cssText = `
            color: white;
            font-size: 14px;
            text-align: center;
            font-weight: 500;
            letter-spacing: 0.5px;
            display: ${CONFIG.showPercentage ? 'block' : 'none'};
        `;
        progressText.textContent = '0%';
        progressContainer.appendChild(progressText);
        
        // Create loading message
        const messageElement = document.createElement('div');
        messageElement.className = 'loader-message';
        messageElement.style.cssText = `
            color: white;
            font-size: 18px;
            font-weight: 500;
            margin-top: 15px;
            text-align: center;
            letter-spacing: 0.5px;
        `;
        messageElement.textContent = CONFIG.message;
        
        const cancelButton = document.createElement('button');
        cancelButton.id = 'loaderCancelButton';
        cancelButton.style.cssText = `
            margin-top: 25px;
            padding: 8px 20px;
            background: rgba(255, 255, 255, 0.1);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s ease;
            opacity: 0.7;
            pointer-events: auto;
        `;
        cancelButton.textContent = 'Cancel';
        cancelButton.addEventListener('mouseenter', () => {
            cancelButton.style.opacity = '1';
            cancelButton.style.background = 'rgba(255, 255, 255, 0.2)';
        });
        cancelButton.addEventListener('mouseleave', () => {
            cancelButton.style.opacity = '0.7';
            cancelButton.style.background = 'rgba(255, 255, 255, 0.1)';
        });
        cancelButton.addEventListener('click', () => {
            dispatchLoaderEvent('cancel');
            hideLoader();
        });
        
        // Assemble loader
        loaderContainer.appendChild(loaderAnimation);
        loaderContainer.appendChild(progressContainer);
        loaderContainer.appendChild(messageElement);
        loaderContainer.appendChild(cancelButton);
        
        // Add to document
        document.body.appendChild(loaderContainer);
        
        // Add keyframes for animation
        addAnimationStyles();
        
        return loaderContainer;
    }
    
    function addAnimationStyles() {
        if (document.getElementById('loaderStyles')) return;
        
        const styleSheet = document.createElement('style');
        styleSheet.id = 'loaderStyles';
        styleSheet.textContent = `
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            @keyframes fadeOut {
                from { opacity: 1; }
                to { opacity: 0; }
            }
        `;
        
        document.head.appendChild(styleSheet);
    }
    
    // Update progress
    function updateProgress(percent) {
        loadProgress = Math.min(100, Math.max(0, percent));
        
        const progressFill = document.getElementById('loaderProgressFill');
        const progressText = document.getElementById('loaderProgressText');
        
        if (progressFill) {
            progressFill.style.width = `${loadProgress}%`;
        }
        
        if (progressText && CONFIG.showPercentage) {
            progressText.textContent = `${Math.round(loadProgress)}%`;
        }
        
        dispatchLoaderEvent('progress', { progress: loadProgress });
    }
    
    function simulateProgress() {
        if (simulatedProgress) return;
        
        simulatedProgress = true;
        loadProgress = 0;
        
        if (progressInterval) clearInterval(progressInterval);
        
        // Fast progress to 80%
        progressInterval = setInterval(() => {
            if (loadProgress < 80) {
                loadProgress += (80 - loadProgress) * 0.1 + 1;
                updateProgress(loadProgress);
            } else {
                clearInterval(progressInterval);
                // Slow progress from 80% to 90%
                progressInterval = setInterval(() => {
                    if (loadProgress < 90) {
                        loadProgress += 0.5;
                        updateProgress(loadProgress);
                    } else {
                        clearInterval(progressInterval);
                    }
                }, 100);
            }
        }, 50);
    }
    
    // Show loader
    function showLoader(message) {
        if (isLoading) return;
        
        isLoading = true;
        simulatedProgress = false;
        loadProgress = 0;
        
        const loader = createLoader();
        
        if (message) {
            const messageElement = loader.querySelector('.loader-message');
            if (messageElement) messageElement.textContent = message;
        }
        
        // Show with animation
        setTimeout(() => {
            loader.style.opacity = '1';
            loader.style.pointerEvents = 'auto';
            
            // Start progress simulation
            if (CONFIG.showProgress) {
                simulateProgress();
            }
        }, 10);
        
        dispatchLoaderEvent('show');
        
        return loader;
    }
    
    // Hide loader
    function hideLoader() {
        if (!isLoading) return;
        
        isLoading = false;
        simulatedProgress = false;
        
        const loader = document.getElementById('modernLoadingIndicator');
        if (!loader) return;
        
        // Complete progress if shown
        if (CONFIG.showProgress) {
            updateProgress(100);
        }
        
        // Hide with animation
        loader.style.opacity = '0';
        loader.style.pointerEvents = 'none';
        
        setTimeout(() => {
            if (loader.parentNode) {
                loader.parentNode.removeChild(loader);
            }
            dispatchLoaderEvent('hide');
        }, 300);
        
        if (progressInterval) {
            clearInterval(progressInterval);
            progressInterval = null;
        }
    }
    
    // Dispatch custom events
    function dispatchLoaderEvent(eventName, detail = {}) {
        const event = new CustomEvent(`loader:${eventName}`, {
            detail: { ...detail, timestamp: Date.now() }
        });
        window.dispatchEvent(event);
    }
    
    // Intercept link clicks
    function setupLinkInterception() {
        if (!CONFIG.enableLinkInterception) return;
        
        document.addEventListener('click', (e) => {
            let target = e.target;
            
            // Find parent link if clicked element is inside a link
            while (target && target !== document) {
                if (target.tagName === 'A' && target.href) {
                    // Check if it's an external link or same-page anchor
                    const isSamePage = target.getAttribute('href')?.startsWith('#');
                    const isExternal = target.target === '_blank' || 
                                      target.hasAttribute('download') ||
                                      target.getAttribute('href')?.startsWith('javascript:') ||
                                      target.getAttribute('href')?.startsWith('mailto:') ||
                                      target.hasAttribute('onclick') || 
                                      target.getAttribute('onclick')?.includes('window.location.href')||
                                      target.getAttribute('href')?.startsWith('tel:');
                    
                    if (!isSamePage && !isExternal) {
                        // Show loader for navigation
                        showLoader('Navigating...');
                    }
                    break;
                }
                target = target.parentNode;
            }
        });
    }
    
    // Setup AJAX interception
    function setupAjaxInterception() {
        if (!CONFIG.enableAjaxInterception) return;
        
        // Store original XMLHttpRequest
        const originalXHR = window.XMLHttpRequest;
        const originalFetch = window.fetch;
        
        // Override XMLHttpRequest
        if (originalXHR) {
            window.XMLHttpRequest = function() {
                const xhr = new originalXHR();
                let isLoading = false;
                
                const originalOpen = xhr.open;
                xhr.open = function(...args) {
                    isLoading = true;
                    showLoader('Loading data...');
                    return originalOpen.apply(this, args);
                };
                
                const originalSend = xhr.send;
                xhr.send = function(...args) {
                    this.addEventListener('loadend', () => {
                        if (isLoading) {
                            setTimeout(hideLoader, 200);
                            isLoading = false;
                        }
                    });
                    return originalSend.apply(this, args);
                };
                
                return xhr;
            };
            
            // Copy static properties
            for (const key in originalXHR) {
                if (Object.prototype.hasOwnProperty.call(originalXHR, key)) {
                    window.XMLHttpRequest[key] = originalXHR[key];
                }
            }
        }
        
        // Override fetch
        if (originalFetch) {
            window.fetch = function(...args) {
                showLoader('Loading data...');
                return originalFetch.apply(this, args)
                    .then(response => {
                        setTimeout(hideLoader, 200);
                        return response;
                    })
                    .catch(error => {
                        setTimeout(hideLoader, 200);
                        throw error;
                    });
            };
        }
    }
    
    // Initialize
    function init(config = {}) {
        // Merge user config with defaults
        Object.assign(CONFIG, config);
        
        // Show loader immediately if page is still loading
        if (document.readyState !== 'complete') {
            showLoader(CONFIG.message);
            
            // Hide when page is fully loaded
            window.addEventListener('load', () => {
                if (CONFIG.autoHide) {
                    setTimeout(hideLoader, CONFIG.hideDelay);
                }
            });
        }
        
        document.addEventListener('DOMContentLoaded', () => {
            if (CONFIG.autoHide && !isLoading) {
                setTimeout(hideLoader, CONFIG.hideDelay);
            }
        });
        
        // Setup link interception
        setupLinkInterception();
        
        // Setup AJAX interception if enabled
        if (CONFIG.enableAjaxInterception) {
            setupAjaxInterception();
        }
        
        // Expose API to window
        window.LoadingIndicator = {
            show: (message) => showLoader(message),
            hide: () => hideLoader(),
            updateProgress: (percent) => updateProgress(percent),
            setConfig: (newConfig) => Object.assign(CONFIG, newConfig),
            isVisible: () => isLoading,
            getProgress: () => loadProgress
        };
        
        dispatchLoaderEvent('init');
    }
    
    // Start initialization when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => init());
    } else {
        init();
    }
    
})();