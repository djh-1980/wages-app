/**
 * Universal Customer Mapping Utilities
 * Provides customer name mapping across the entire site
 */

class CustomerMappingService {
    constructor() {
        this.mappings = new Map();
        this.loaded = false;
        this.loading = false;
    }

    /**
     * Load customer mappings from the API
     */
    async loadMappings() {
        if (this.loaded || this.loading) {
            return this.mappings;
        }

        this.loading = true;
        
        try {
            const response = await fetch('/api/customer-mapping/mappings');
            const result = await response.json();
            
            if (result.success) {
                // Build mapping lookup
                this.mappings.clear();
                result.mappings.forEach(mapping => {
                    this.mappings.set(mapping.original_customer, mapping.mapped_customer);
                });
                
                this.loaded = true;
                console.log(`Loaded ${this.mappings.size} customer mappings`);
            }
        } catch (error) {
            console.error('Error loading customer mappings:', error);
        } finally {
            this.loading = false;
        }
        
        return this.mappings;
    }

    /**
     * Get the mapped customer name (or original if no mapping exists)
     */
    getMappedCustomer(originalCustomer) {
        if (!originalCustomer) return originalCustomer;
        
        return this.mappings.get(originalCustomer) || originalCustomer;
    }

    /**
     * Apply mappings to an array of objects with customer field
     */
    applyMappingsToArray(items, customerField = 'customer') {
        return items.map(item => ({
            ...item,
            [`${customerField}_original`]: item[customerField], // Preserve original
            [customerField]: this.getMappedCustomer(item[customerField]) // Apply mapping
        }));
    }

    /**
     * Apply mappings to a single object
     */
    applyMappingToObject(item, customerField = 'customer') {
        if (!item || !item[customerField]) return item;
        
        return {
            ...item,
            [`${customerField}_original`]: item[customerField], // Preserve original
            [customerField]: this.getMappedCustomer(item[customerField]) // Apply mapping
        };
    }

    /**
     * Group items by mapped customer name
     */
    groupByMappedCustomer(items, customerField = 'customer') {
        const groups = {};
        
        items.forEach(item => {
            const mappedCustomer = this.getMappedCustomer(item[customerField]);
            if (!groups[mappedCustomer]) {
                groups[mappedCustomer] = [];
            }
            groups[mappedCustomer].push({
                ...item,
                [`${customerField}_original`]: item[customerField]
            });
        });
        
        return groups;
    }

    /**
     * Get aggregated stats by mapped customer
     */
    getAggregatedStats(items, customerField = 'customer', valueFields = []) {
        const groups = this.groupByMappedCustomer(items, customerField);
        const stats = {};
        
        Object.keys(groups).forEach(mappedCustomer => {
            const groupItems = groups[mappedCustomer];
            const stat = {
                customer: mappedCustomer,
                count: groupItems.length,
                original_customers: [...new Set(groupItems.map(item => item[`${customerField}_original`]))]
            };
            
            // Aggregate numeric fields
            valueFields.forEach(field => {
                stat[field] = groupItems.reduce((sum, item) => {
                    const value = parseFloat(item[field]) || 0;
                    return sum + value;
                }, 0);
            });
            
            stats[mappedCustomer] = stat;
        });
        
        return stats;
    }

    /**
     * Initialize mappings and apply to page elements
     */
    async initializeForPage() {
        await this.loadMappings();
        
        // Apply mappings to existing elements with data-customer attribute
        document.querySelectorAll('[data-customer]').forEach(element => {
            const originalCustomer = element.getAttribute('data-customer');
            const mappedCustomer = this.getMappedCustomer(originalCustomer);
            
            if (mappedCustomer !== originalCustomer) {
                // Store original in a data attribute
                element.setAttribute('data-customer-original', originalCustomer);
                element.setAttribute('data-customer', mappedCustomer);
                
                // Update text content if it matches the customer name
                if (element.textContent.trim() === originalCustomer) {
                    element.textContent = mappedCustomer;
                }
            }
        });
        
        // Trigger custom event for pages to handle mapping updates
        document.dispatchEvent(new CustomEvent('customerMappingsLoaded', {
            detail: { mappings: this.mappings }
        }));
    }

    /**
     * Refresh mappings (call after creating/updating mappings)
     */
    async refresh() {
        this.loaded = false;
        this.mappings.clear();
        await this.loadMappings();
        
        // Re-apply to page
        document.dispatchEvent(new CustomEvent('customerMappingsUpdated', {
            detail: { mappings: this.mappings }
        }));
    }
}

// Create global instance
window.customerMapping = new CustomerMappingService();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.customerMapping.initializeForPage();
});

// Utility functions for backward compatibility
window.getMappedCustomer = (customer) => window.customerMapping.getMappedCustomer(customer);
window.applyCustomerMappings = (items, field) => window.customerMapping.applyMappingsToArray(items, field);
