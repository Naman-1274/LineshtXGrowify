# core/session_manager.py - Enhanced session state management with step-based workflow
import streamlit as st

class SessionManager:
    """Enhanced session management with step-based workflow and description elements"""
    
    def __init__(self):
        self._required_keys = [
            'step', 'column_assignments', 'enhanced_column_mapping', 'column_descriptions',
            'column_html_tags', 'variant_quantities', 'variant_compare_prices',
            'description_elements', 'column_mapping_complete'
        ]
    
    def initialize(self):
        """Initialize all required session state variables with defaults"""
        defaults = {
            'step': 1,
            'df_raw': None,
            'column_mapping': {},
            'column_mapping_complete': False,
            'description_elements': [],
            'processed_data': None,
            'config': {
                'mode': 'Default template (no AI)',
                'vendor_name': 'YourBrandName',
                'inventory_policy': 'deny',
                'default_qty': 10,
                'default_compare_price': 0.0,
                'enable_surcharge': False,
                'surcharge_rules': {},
                'bulk_qty_mode': False,
                'bulk_compare_price_mode': False
            }
        }
        
        # Initialize defaults
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
        
        # Initialize additional required keys
        for key in self._required_keys:
            if key not in st.session_state:
                if key in ['column_assignments', 'enhanced_column_mapping', 'column_descriptions',
                          'column_html_tags', 'variant_quantities', 'variant_compare_prices']:
                    st.session_state[key] = {}
                elif key == 'description_elements':
                    st.session_state[key] = []
                elif key == 'step':
                    st.session_state[key] = 1
                elif key == 'column_mapping_complete':
                    st.session_state[key] = False
    
    def get_current_step(self):
        """Get current workflow step"""
        return st.session_state.get('step', 1)
    
    def set_current_step(self, step):
        """Set current workflow step"""
        st.session_state.step = step
    
    def get(self, key, default=None):
        """Get session state value"""
        return st.session_state.get(key, default)
    
    def set(self, key, value):
        """Set session state value"""
        st.session_state[key] = value
    
    def update_config(self, config):
        """Update configuration in session state"""
        st.session_state.config.update(config)
    
    def get_config(self):
        """Get current configuration"""
        return st.session_state.get('config', {})
    
    def store_mappings(self, column_mapping, column_descriptions=None):
        """Store column mappings and descriptions"""
        st.session_state.column_mapping = column_mapping
        if column_descriptions:
            st.session_state.column_descriptions = column_descriptions
    
    def get_mappings(self):
        """Get current column mappings"""
        return st.session_state.get('column_mapping', {})
    
    def get_descriptions(self):
        """Get current column descriptions"""
        return st.session_state.get('column_descriptions', {})
    
    def get_description_elements(self):
        """Get description elements for dynamic builder"""
        return st.session_state.get('description_elements', [])
    
    def set_description_elements(self, elements):
        """Set description elements"""
        st.session_state.description_elements = elements
    
    def add_description_element(self, element=None):
        """Add new description element"""
        if element is None:
            element = {
                'column': '',
                'label': '',
                'html_tag': 'p',
                'order': len(st.session_state.description_elements) + 1
            }
        st.session_state.description_elements.append(element)
    
    def remove_last_description_element(self):
        """Remove last description element"""
        if st.session_state.description_elements:
            st.session_state.description_elements.pop()
    
    def get_variants(self):
        """Get variant data including extracted quantities"""
        return {
            'unique_variants': st.session_state.get('unique_variants', []),
            'variant_products': st.session_state.get('variant_products', {}),
            'variant_quantities': st.session_state.get('variant_quantities', {}),
            'variant_compare_prices': st.session_state.get('variant_compare_prices', {}),
            'extracted_quantities': st.session_state.get('extracted_quantities', {}),
            'extracted_compare_prices': st.session_state.get('extracted_compare_prices', {})
        }
    
    def is_mapping_complete(self):
        """Check if column mapping is complete"""
        return st.session_state.get('column_mapping_complete', False)
    
    def set_mapping_complete(self, complete=True):
        """Set column mapping completion status"""
        st.session_state.column_mapping_complete = complete
    
    def clear_mapping_data(self):
        """Clear mapping-related session data"""
        mapping_keys = [
            'column_mapping', 'column_mapping_complete', 'column_assignments',
            'enhanced_column_mapping', 'column_descriptions', 'column_html_tags',
            'description_elements'
        ]
        for key in mapping_keys:
            if key in st.session_state:
                if key == 'description_elements':
                    st.session_state[key] = []
                elif key in ['column_assignments', 'enhanced_column_mapping', 
                           'column_descriptions', 'column_html_tags']:
                    st.session_state[key] = {}
                elif key == 'column_mapping_complete':
                    st.session_state[key] = False
                else:
                    del st.session_state[key]
    
    def clear_all_data(self):
        """Clear all session data for new file"""
        clear_keys = [
            'processed_data', 'df_raw', 'column_mapping_complete',
            'unique_variants', 'variant_quantities', 'variant_compare_prices',
            'variant_products', 'description_elements'
        ]
        for key in clear_keys:
            if key in st.session_state:
                if key == 'description_elements':
                    st.session_state[key] = []
                else:
                    del st.session_state[key]
        
        # Reset step to 1
        st.session_state.step = 1
        
        # Re-initialize required keys
        self.initialize()
    
    def reset_session(self):
        """Reset entire session to start over"""
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        self.initialize()