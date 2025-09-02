/**
 * Cuti Components - Unified JavaScript Component Library
 * Provides reusable UI components and utilities
 */

const CutiComponents = (function() {
    'use strict';

    // Component Registry
    const components = new Map();
    const eventBus = new EventTarget();

    // Utility Functions
    const utils = {
        /**
         * Debounce function execution
         */
        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },

        /**
         * Format numbers with commas
         */
        formatNumber(num) {
            return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        },

        /**
         * Format bytes to human readable
         */
        formatBytes(bytes, decimals = 2) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const dm = decimals < 0 ? 0 : decimals;
            const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
        },

        /**
         * Generate unique ID
         */
        generateId(prefix = 'cuti') {
            return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        },

        /**
         * Deep merge objects
         */
        deepMerge(target, ...sources) {
            if (!sources.length) return target;
            const source = sources.shift();

            if (this.isObject(target) && this.isObject(source)) {
                for (const key in source) {
                    if (this.isObject(source[key])) {
                        if (!target[key]) Object.assign(target, { [key]: {} });
                        this.deepMerge(target[key], source[key]);
                    } else {
                        Object.assign(target, { [key]: source[key] });
                    }
                }
            }
            return this.deepMerge(target, ...sources);
        },

        isObject(item) {
            return item && typeof item === 'object' && !Array.isArray(item);
        }
    };

    // Toast Notification System
    class ToastManager {
        constructor() {
            this.container = null;
            this.init();
        }

        init() {
            if (!document.getElementById('toast-container')) {
                this.container = document.createElement('div');
                this.container.id = 'toast-container';
                this.container.className = 'toast-container';
                document.body.appendChild(this.container);
            } else {
                this.container = document.getElementById('toast-container');
            }
        }

        show(message, type = 'info', duration = 5000) {
            const toast = document.createElement('div');
            toast.className = `toast toast-${type} toast-enter`;
            
            const icon = {
                success: '✓',
                error: '⚠',
                warning: '⚠',
                info: 'ℹ'
            }[type] || 'ℹ';

            toast.innerHTML = `
                <span class="toast-icon">${icon}</span>
                <span class="toast-message">${message}</span>
                <button class="toast-close" onclick="this.parentElement.remove()">×</button>
            `;

            this.container.appendChild(toast);

            // Trigger animation
            requestAnimationFrame(() => {
                toast.classList.remove('toast-enter');
                toast.classList.add('toast-active');
            });

            // Auto remove
            if (duration > 0) {
                setTimeout(() => {
                    toast.classList.add('toast-exit');
                    setTimeout(() => toast.remove(), 300);
                }, duration);
            }

            return toast;
        }

        success(message, duration) {
            return this.show(message, 'success', duration);
        }

        error(message, duration) {
            return this.show(message, 'error', duration);
        }

        warning(message, duration) {
            return this.show(message, 'warning', duration);
        }

        info(message, duration) {
            return this.show(message, 'info', duration);
        }
    }

    // Modal Manager
    class ModalManager {
        constructor() {
            this.modals = new Map();
            this.activeModal = null;
            this.init();
        }

        init() {
            // Close modal on escape key
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.activeModal) {
                    this.close(this.activeModal);
                }
            });
        }

        register(id, options = {}) {
            this.modals.set(id, {
                element: document.getElementById(id),
                options
            });
        }

        open(id) {
            const modal = this.modals.get(id);
            if (!modal) {
                console.error(`Modal ${id} not found`);
                return;
            }

            // Close current modal if exists
            if (this.activeModal) {
                this.close(this.activeModal);
            }

            modal.element.classList.add('modal-open');
            document.body.classList.add('modal-active');
            this.activeModal = id;

            eventBus.dispatchEvent(new CustomEvent('modal:opened', { detail: { id } }));
        }

        close(id) {
            const modal = this.modals.get(id);
            if (!modal) return;

            modal.element.classList.remove('modal-open');
            document.body.classList.remove('modal-active');
            this.activeModal = null;

            eventBus.dispatchEvent(new CustomEvent('modal:closed', { detail: { id } }));
        }

        toggle(id) {
            if (this.activeModal === id) {
                this.close(id);
            } else {
                this.open(id);
            }
        }
    }

    // Form Validator
    class FormValidator {
        constructor(formElement, rules = {}) {
            this.form = formElement;
            this.rules = rules;
            this.errors = {};
            this.init();
        }

        init() {
            this.form.addEventListener('submit', (e) => {
                if (!this.validate()) {
                    e.preventDefault();
                    this.showErrors();
                }
            });

            // Real-time validation
            this.form.querySelectorAll('input, select, textarea').forEach(field => {
                field.addEventListener('blur', () => {
                    this.validateField(field);
                });
            });
        }

        validate() {
            this.errors = {};
            let isValid = true;

            Object.keys(this.rules).forEach(fieldName => {
                const field = this.form.querySelector(`[name="${fieldName}"]`);
                if (!field) return;

                if (!this.validateField(field)) {
                    isValid = false;
                }
            });

            return isValid;
        }

        validateField(field) {
            const fieldName = field.name;
            const rules = this.rules[fieldName];
            if (!rules) return true;

            const value = field.value;
            let isValid = true;

            // Required validation
            if (rules.required && !value) {
                this.errors[fieldName] = `${fieldName} is required`;
                isValid = false;
            }

            // Min length validation
            if (rules.minLength && value.length < rules.minLength) {
                this.errors[fieldName] = `${fieldName} must be at least ${rules.minLength} characters`;
                isValid = false;
            }

            // Max length validation
            if (rules.maxLength && value.length > rules.maxLength) {
                this.errors[fieldName] = `${fieldName} must be no more than ${rules.maxLength} characters`;
                isValid = false;
            }

            // Email validation
            if (rules.email && value) {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(value)) {
                    this.errors[fieldName] = `${fieldName} must be a valid email`;
                    isValid = false;
                }
            }

            // Custom validation
            if (rules.custom && typeof rules.custom === 'function') {
                const customError = rules.custom(value, field);
                if (customError) {
                    this.errors[fieldName] = customError;
                    isValid = false;
                }
            }

            // Update field UI
            this.updateFieldUI(field, isValid);

            return isValid;
        }

        updateFieldUI(field, isValid) {
            const formGroup = field.closest('.form-group');
            if (!formGroup) return;

            // Remove existing error
            const existingError = formGroup.querySelector('.form-error');
            if (existingError) existingError.remove();

            if (!isValid) {
                field.classList.add('is-invalid');
                field.classList.remove('is-valid');

                const errorElement = document.createElement('div');
                errorElement.className = 'form-error';
                errorElement.textContent = this.errors[field.name];
                formGroup.appendChild(errorElement);
            } else {
                field.classList.remove('is-invalid');
                field.classList.add('is-valid');
            }
        }

        showErrors() {
            Object.keys(this.errors).forEach(fieldName => {
                const field = this.form.querySelector(`[name="${fieldName}"]`);
                if (field) {
                    this.updateFieldUI(field, false);
                }
            });
        }
    }

    // Data Table Component
    class DataTable {
        constructor(element, options = {}) {
            this.element = element;
            this.options = {
                data: [],
                columns: [],
                pageSize: 10,
                sortable: true,
                searchable: true,
                paginate: true,
                ...options
            };
            this.currentPage = 1;
            this.sortColumn = null;
            this.sortDirection = 'asc';
            this.searchTerm = '';
            this.init();
        }

        init() {
            this.render();
            this.attachEventListeners();
        }

        render() {
            const filteredData = this.getFilteredData();
            const paginatedData = this.getPaginatedData(filteredData);
            
            let html = '';

            // Search box
            if (this.options.searchable) {
                html += `
                    <div class="table-search">
                        <input type="text" class="table-search-input" placeholder="Search..." value="${this.searchTerm}">
                    </div>
                `;
            }

            // Table
            html += '<div class="table-responsive"><table class="data-table"><thead><tr>';
            
            // Headers
            this.options.columns.forEach(column => {
                const sortIcon = this.sortColumn === column.field ? 
                    (this.sortDirection === 'asc' ? '↑' : '↓') : '';
                html += `
                    <th ${this.options.sortable ? `class="sortable" data-field="${column.field}"` : ''}>
                        ${column.label} ${sortIcon}
                    </th>
                `;
            });
            html += '</tr></thead><tbody>';

            // Rows
            paginatedData.forEach(row => {
                html += '<tr>';
                this.options.columns.forEach(column => {
                    const value = column.render ? column.render(row[column.field], row) : row[column.field];
                    html += `<td>${value}</td>`;
                });
                html += '</tr>';
            });

            html += '</tbody></table></div>';

            // Pagination
            if (this.options.paginate) {
                html += this.renderPagination(filteredData.length);
            }

            this.element.innerHTML = html;
        }

        renderPagination(totalItems) {
            const totalPages = Math.ceil(totalItems / this.options.pageSize);
            let html = '<div class="table-pagination">';
            
            // Previous button
            html += `<button class="pagination-btn" data-page="${this.currentPage - 1}" 
                     ${this.currentPage === 1 ? 'disabled' : ''}>Previous</button>`;
            
            // Page numbers
            for (let i = 1; i <= totalPages; i++) {
                if (i === 1 || i === totalPages || (i >= this.currentPage - 2 && i <= this.currentPage + 2)) {
                    html += `<button class="pagination-btn ${i === this.currentPage ? 'active' : ''}" 
                             data-page="${i}">${i}</button>`;
                } else if (i === this.currentPage - 3 || i === this.currentPage + 3) {
                    html += '<span>...</span>';
                }
            }
            
            // Next button
            html += `<button class="pagination-btn" data-page="${this.currentPage + 1}" 
                     ${this.currentPage === totalPages ? 'disabled' : ''}>Next</button>`;
            
            html += '</div>';
            return html;
        }

        getFilteredData() {
            let data = [...this.options.data];

            // Search filter
            if (this.searchTerm) {
                data = data.filter(row => {
                    return this.options.columns.some(column => {
                        const value = row[column.field];
                        return value && value.toString().toLowerCase().includes(this.searchTerm.toLowerCase());
                    });
                });
            }

            // Sort
            if (this.sortColumn) {
                data.sort((a, b) => {
                    const aVal = a[this.sortColumn];
                    const bVal = b[this.sortColumn];
                    
                    if (aVal < bVal) return this.sortDirection === 'asc' ? -1 : 1;
                    if (aVal > bVal) return this.sortDirection === 'asc' ? 1 : -1;
                    return 0;
                });
            }

            return data;
        }

        getPaginatedData(data) {
            if (!this.options.paginate) return data;
            
            const start = (this.currentPage - 1) * this.options.pageSize;
            const end = start + this.options.pageSize;
            return data.slice(start, end);
        }

        attachEventListeners() {
            // Search
            this.element.addEventListener('input', (e) => {
                if (e.target.classList.contains('table-search-input')) {
                    this.searchTerm = e.target.value;
                    this.currentPage = 1;
                    this.render();
                }
            });

            // Sort
            this.element.addEventListener('click', (e) => {
                if (e.target.classList.contains('sortable')) {
                    const field = e.target.dataset.field;
                    if (this.sortColumn === field) {
                        this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
                    } else {
                        this.sortColumn = field;
                        this.sortDirection = 'asc';
                    }
                    this.render();
                }

                // Pagination
                if (e.target.classList.contains('pagination-btn') && !e.target.disabled) {
                    this.currentPage = parseInt(e.target.dataset.page);
                    this.render();
                }
            });
        }

        updateData(data) {
            this.options.data = data;
            this.render();
        }
    }

    // Toggle Switch Component
    class ToggleSwitch {
        constructor(element, options = {}) {
            this.element = element;
            this.checkbox = element.querySelector('input[type="checkbox"]');
            this.options = {
                onChange: null,
                ...options
            };
            this.init();
        }

        init() {
            this.element.addEventListener('click', () => {
                this.toggle();
            });
        }

        toggle() {
            this.checkbox.checked = !this.checkbox.checked;
            this.element.classList.toggle('active', this.checkbox.checked);
            
            if (this.options.onChange) {
                this.options.onChange(this.checkbox.checked);
            }

            eventBus.dispatchEvent(new CustomEvent('toggle:changed', {
                detail: {
                    element: this.element,
                    checked: this.checkbox.checked
                }
            }));
        }

        setValue(checked) {
            this.checkbox.checked = checked;
            this.element.classList.toggle('active', checked);
        }

        getValue() {
            return this.checkbox.checked;
        }
    }

    // API Client
    class ApiClient {
        constructor(baseURL = '') {
            this.baseURL = baseURL;
        }

        async request(url, options = {}) {
            const config = {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            };

            try {
                const response = await fetch(this.baseURL + url, config);
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                return { success: true, data };
            } catch (error) {
                console.error('API request failed:', error);
                return { success: false, error: error.message };
            }
        }

        get(url, options = {}) {
            return this.request(url, { ...options, method: 'GET' });
        }

        post(url, data, options = {}) {
            return this.request(url, {
                ...options,
                method: 'POST',
                body: JSON.stringify(data)
            });
        }

        put(url, data, options = {}) {
            return this.request(url, {
                ...options,
                method: 'PUT',
                body: JSON.stringify(data)
            });
        }

        delete(url, options = {}) {
            return this.request(url, { ...options, method: 'DELETE' });
        }
    }

    // Initialize components
    const toast = new ToastManager();
    const modal = new ModalManager();
    const api = new ApiClient('/api');

    // Auto-initialize components
    function autoInit() {
        // Initialize all toggle switches
        document.querySelectorAll('.toggle-switch').forEach(element => {
            if (!element.dataset.initialized) {
                new ToggleSwitch(element);
                element.dataset.initialized = 'true';
            }
        });

        // Initialize all modals
        document.querySelectorAll('.modal').forEach(element => {
            if (!element.dataset.initialized) {
                modal.register(element.id);
                element.dataset.initialized = 'true';
            }
        });

        // Initialize form validators
        document.querySelectorAll('form[data-validate]').forEach(form => {
            if (!form.dataset.initialized) {
                const rules = JSON.parse(form.dataset.validateRules || '{}');
                new FormValidator(form, rules);
                form.dataset.initialized = 'true';
            }
        });
    }

    // Auto-init on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', autoInit);
    } else {
        autoInit();
    }

    // Public API
    return {
        utils,
        toast,
        modal,
        api,
        eventBus,
        components: {
            ToastManager,
            ModalManager,
            FormValidator,
            DataTable,
            ToggleSwitch
        },
        init: autoInit
    };
})();

// Make it globally available
window.CutiComponents = CutiComponents;

// Shorthand aliases
window.$toast = CutiComponents.toast;
window.$modal = CutiComponents.modal;
window.$api = CutiComponents.api;