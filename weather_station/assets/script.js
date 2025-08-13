/**
 * Weather Station JavaScript v2.0
 * Enhanced functionality with automatic data updates and freshness tracking
 */

class WeatherStation {
    constructor() {
        this.dataCache = null;
        this.dataCacheTime = 0;
        this.dataStatus = null;
        this.statusCheckInterval = null;
        this.init();
    }

    init() {
        this.setupGlobalHandlers();
        this.addAnimations();
        this.enhanceUserExperience();
        this.setupDataStatusMonitoring();
        this.loadWeatherData();
    }

    setupDataStatusMonitoring() {
        // Check data status every 5 minutes
        this.checkDataStatus();
        this.statusCheckInterval = setInterval(() => {
            this.checkDataStatus();
        }, 300000); // 5 minutes
        
        // Add status indicator to navbar if it exists
        this.addDataStatusIndicator();
    }

    async checkDataStatus() {
        try {
            const response = await fetch('/api/data/status');
            if (response.ok) {
                this.dataStatus = await response.json();
                this.updateStatusIndicator();
                
                // If data needs updating, show notification
                if (this.dataStatus.needs_update && this.dataStatus.auto_update_enabled) {
                    this.showDataUpdateNotification();
                }
            }
        } catch (error) {
            console.warn('Failed to check data status:', error);
        }
    }

    addDataStatusIndicator() {
        const navbar = document.querySelector('.navbar');
        if (!navbar) return;

        const statusIndicator = document.createElement('div');
        statusIndicator.id = 'data-status-indicator';
        statusIndicator.className = 'data-status-indicator';
        statusIndicator.innerHTML = `
            <span id="status-icon" class="status-icon">🌐</span>
            <span id="status-text" class="status-text">Live Data</span>
        `;
        
        // Add to navbar
        const navbarNav = navbar.querySelector('.navbar-nav');
        if (navbarNav) {
            const statusLi = document.createElement('li');
            statusLi.className = 'nav-item';
            statusLi.appendChild(statusIndicator);
            navbarNav.appendChild(statusLi);
        }

        // Add CSS for status indicator
        this.addStatusIndicatorStyles();
    }

    addStatusIndicatorStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .data-status-indicator {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.5rem 1rem;
                border-radius: 20px;
                background: rgba(255,255,255,0.1);
                color: white;
                font-size: 0.875rem;
                cursor: pointer;
            }
            
            .data-status-indicator:hover {
                background: rgba(255,255,255,0.2);
            }
            
            .status-icon {
                font-size: 1rem;
            }
            
            .status-fresh { background: rgba(40, 167, 69, 0.8); }
            .status-updating { background: rgba(255, 193, 7, 0.8); }
            .status-stale { background: rgba(220, 53, 69, 0.8); }
            
            @media (max-width: 768px) {
                .status-text { display: none; }
            }
        `;
        document.head.appendChild(style);
    }

    updateStatusIndicator() {
        const statusIcon = document.getElementById('status-icon');
        const statusText = document.getElementById('status-text');
        const indicator = document.getElementById('data-status-indicator');
        
        if (!this.dataStatus || !statusIcon || !statusText || !indicator) return;

        const info = this.dataStatus.data_info;
        const cache = this.dataStatus.cache_status;
        const apiAccessible = info.api_accessible;
        
        // Reset classes
        indicator.className = 'data-status-indicator';
        
        if (cache.has_cache && cache.cache_fresh) {
            statusIcon.textContent = '⚡';
            statusText.textContent = `Cached (${cache.cached_locations})`;
            indicator.classList.add('status-fresh');
        } else if (apiAccessible && info.location_count > 0) {
            statusIcon.textContent = '🌐';
            statusText.textContent = `Live (${info.location_count})`;
            indicator.classList.add('status-fresh');
        } else if (!apiAccessible) {
            statusIcon.textContent = '❌';
            statusText.textContent = 'API Down';
            indicator.classList.add('status-stale');
        } else {
            statusIcon.textContent = '🔄';
            statusText.textContent = 'Loading...';
            indicator.classList.add('status-updating');
        }
        
        // Add click handler for manual update
        indicator.onclick = () => this.showDataStatusModal();
    }

    showDataUpdateNotification() {
        // Don't spam notifications
        if (this.lastNotificationTime && Date.now() - this.lastNotificationTime < 300000) {
            return;
        }
        
        const notification = document.createElement('div');
        notification.className = 'alert alert-info alert-dismissible fade show data-notification';
        notification.innerHTML = `
            <strong>Data Update Available</strong>
            Weather data is being updated automatically in the background.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Insert at top of main container
        const container = document.querySelector('.main-container, .container');
        if (container) {
            container.insertBefore(notification, container.firstChild);
            
            // Auto-hide after 10 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 10000);
        }
        
        this.lastNotificationTime = Date.now();
    }

    showDataStatusModal() {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">🌤️ Data Status</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        ${this.renderDataStatusInfo()}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // Clean up when modal is hidden
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
    }

    renderDataStatusInfo() {
        if (!this.dataStatus) return '<p>Status information not available.</p>';
        
        const info = this.dataStatus.data_info;
        const fileStatus = this.dataStatus.file_status;
        
        return `
            <div class="row g-3">
                <div class="col-md-6">
                    <strong>Data File Status:</strong><br>
                    ${fileStatus?.exists ? '✅' : '❌'} ${fileStatus?.exists ? 'Present' : 'Missing'}<br>
                    <small>${(fileStatus?.size_mb || 0).toFixed(1)} MB</small>
                </div>
                <div class="col-md-6">
                    <strong>Data Age:</strong><br>
                    ${fileStatus?.age || 'Unknown'}<br>
                    <small>${this.dataStatus.file_based ? 'File-based storage' : 'Live system'}</small>
                </div>
                <div class="col-md-6">
                    <strong>Auto-Update:</strong><br>
                    ${this.dataStatus.auto_update_enabled ? '✅' : '❌'} ${this.dataStatus.auto_update_enabled ? 'Enabled' : 'Disabled'}<br>
                    <small>Every ${Math.round(this.dataStatus.update_interval_hours || 168)} hours</small>
                </div>
                <div class="col-md-6">
                    <strong>Locations:</strong><br>
                    ${info.location_count || 0} cities<br>
                    <small>Retention: ${info.retention_days || 16} days</small>
                </div>
            </div>
            ${fileStatus?.valid ? 
                '<div class="alert alert-success mt-3"><strong>✅ Data is Current</strong><br>Within acceptable freshness limits.</div>' :
                !fileStatus?.exists ?
                    '<div class="alert alert-danger mt-3"><strong>❌ No Data File</strong><br>Data file needs to be created. This may take several minutes.</div>' : 
                    '<div class="alert alert-warning mt-3"><strong>⚠️ Data File Issues</strong><br>Data file exists but may be invalid or empty.</div>'
            }
        `;
    }


    showUpdateProgressNotification() {
        const notification = document.createElement('div');
        notification.id = 'update-progress-notification';
        notification.className = 'alert alert-info alert-dismissible show';
        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                <span><strong>Updating weather data...</strong> This may take a few minutes.</span>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        const container = document.querySelector('.main-container, .container');
        if (container) {
            container.insertBefore(notification, container.firstChild);
        }
    }

    showSuccessNotification(message) {
        this.removeUpdateProgressNotification();
        this.showNotification(message, 'success');
    }

    showErrorNotification(message) {
        this.removeUpdateProgressNotification();
        this.showNotification(message, 'danger');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.main-container, .container');
        if (container) {
            container.insertBefore(notification, container.firstChild);
            
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 5000);
        }
    }

    removeUpdateProgressNotification() {
        const notification = document.getElementById('update-progress-notification');
        if (notification) {
            notification.remove();
        }
    }

    async loadWeatherData(forceRefresh = false) {
        // Use cache if recent (3 minutes) and not forcing refresh
        const now = Date.now();
        if (!forceRefresh && this.dataCache && (now - this.dataCacheTime) < 180000) {
            return this.dataCache;
        }
        
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout
            
            const response = await fetch('/api/data/weather', {
                signal: controller.signal,
                headers: {
                    'Cache-Control': forceRefresh ? 'no-cache' : 'max-age=180'
                }
            });
            
            clearTimeout(timeoutId);
            
            if (response.ok) {
                const result = await response.json();
                this.dataCache = result.data;
                this.dataCacheTime = now;
                
                // Trigger custom event for data load
                window.dispatchEvent(new CustomEvent('weatherDataLoaded', { 
                    detail: { 
                        data: this.dataCache, 
                        locations: result.locations,
                        isLive: result.live_data || false,
                        timestamp: result.timestamp
                    } 
                }));
                
                return this.dataCache;
            } else if (response.status === 404) {
                const error = await response.json();
                this.showErrorNotification(`⚠️ ${error.message || 'Weather data not available'}`);
                return null;
            } else if (response.status === 503) {
                const error = await response.json();
                this.showErrorNotification(`🔧 ${error.message || 'Service temporarily unavailable'}`);
                return null;
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                this.showErrorNotification('⏰ Request timed out - please try again');
            } else if (error.message.includes('fetch')) {
                this.showErrorNotification('🌐 Network error - check your connection');
            } else {
                this.showErrorNotification(`❌ Failed to load weather data: ${error.message}`);
            }
            return null;
        }
    }

    setupGlobalHandlers() {
        // Add loading states for forms
        document.addEventListener('submit', (e) => {
            const form = e.target;
            if (form.tagName === 'FORM') {
                this.showLoadingState(form);
            }
        });

        // Add smooth scrolling to internal links
        document.addEventListener('click', (e) => {
            if (e.target.tagName === 'A' && e.target.getAttribute('href')?.startsWith('#')) {
                e.preventDefault();
                const target = document.querySelector(e.target.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            }
        });

        // Add keyboard navigation support
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModals();
            }
        });
    }

    addAnimations() {
        // Intersection Observer for fade-in animations
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        // Observe cards and main content
        document.querySelectorAll('.card, .weather-metric, .stats-card').forEach(el => {
            observer.observe(el);
        });
    }

    enhanceUserExperience() {
        // Add tooltips to complex elements
        this.addTooltips();
        
        // Add loading indicators for async operations
        this.setupLoadingIndicators();
        
        // Enhance form validation
        this.setupFormValidation();
    }

    addTooltips() {
        // Add tooltips to statistical terms
        const tooltipData = {
            'Mean': 'The average value of all data points',
            'Median': 'The middle value when data is sorted',
            'Mode': 'The most frequently occurring value',
            'Standard Deviation': 'Measure of variability in the data'
        };

        Object.keys(tooltipData).forEach(term => {
            const elements = document.querySelectorAll(`[data-tooltip="${term}"]`);
            elements.forEach(el => {
                el.setAttribute('title', tooltipData[term]);
                el.style.cursor = 'help';
            });
        });
    }

    setupLoadingIndicators() {
        // Create loading spinner element
        const createSpinner = () => {
            const spinner = document.createElement('div');
            spinner.className = 'spinner-border text-primary';
            spinner.setAttribute('role', 'status');
            spinner.innerHTML = '<span class="visually-hidden">Loading...</span>';
            return spinner;
        };

        // Add spinner to elements that load data
        window.showLoadingSpinner = (element) => {
            const spinner = createSpinner();
            element.appendChild(spinner);
            return spinner;
        };

        window.hideLoadingSpinner = (spinner) => {
            if (spinner && spinner.parentNode) {
                spinner.parentNode.removeChild(spinner);
            }
        };
    }

    setupFormValidation() {
        // Enhanced form validation
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                if (!this.validateForm(form)) {
                    e.preventDefault();
                    this.showValidationErrors(form);
                }
            });
        });
    }

    validateForm(form) {
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.classList.add('is-invalid');
                isValid = false;
            } else {
                field.classList.remove('is-invalid');
            }
        });

        return isValid;
    }

    showValidationErrors(form) {
        const firstInvalidField = form.querySelector('.is-invalid');
        if (firstInvalidField) {
            firstInvalidField.focus();
            firstInvalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    showLoadingState(element) {
        element.style.opacity = '0.7';
        element.style.pointerEvents = 'none';
    }

    closeModals() {
        // Close any open modals or dropdowns
        const openModals = document.querySelectorAll('.modal.show');
        openModals.forEach(modal => {
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) {
                modalInstance.hide();
            }
        });
    }

    // Utility function for debouncing
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Utility function for throttling
    static throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    // Format numbers for display
    static formatNumber(num, decimals = 2) {
        if (typeof num !== 'number') return num;
        return num.toLocaleString('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    }

    // Format dates for display
    static formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    // Error handling utility
    static handleError(error, context = 'Unknown') {
        console.error(`Error in ${context}:`, error);
        
        // Show user-friendly error message
        const errorMessage = document.createElement('div');
        errorMessage.className = 'alert alert-danger alert-dismissible fade show';
        errorMessage.innerHTML = `
            <strong>Oops!</strong> Something went wrong while loading ${context.toLowerCase()}.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Insert error message at the top of the main container
        const container = document.querySelector('.main-container, .container');
        if (container) {
            container.insertBefore(errorMessage, container.firstChild);
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                errorMessage.remove();
            }, 5000);
        }
    }
}

// Initialize Weather Station when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.weatherStation = new WeatherStation();
});

// Export utilities for use in other scripts
window.WeatherUtils = {
    debounce: WeatherStation.debounce,
    throttle: WeatherStation.throttle,
    formatNumber: WeatherStation.formatNumber,
    formatDate: WeatherStation.formatDate,
    handleError: WeatherStation.handleError
};