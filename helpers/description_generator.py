# helpers/description_generator.py - CLEANED: Only dynamic description system
import pandas as pd
import streamlit as st

class DescriptionGenerator:
    """Unified description generator - ONLY dynamic description builder"""
    
    def apply_enhanced_descriptions(self, df: pd.DataFrame, column_mapping: dict, column_descriptions: dict = None) -> pd.DataFrame:
        """Apply dynamic HTML descriptions from description builder"""
        try:
            # Get description elements from session state
            description_elements = st.session_state.get('description_elements', [])
            
            if not description_elements:
                # No description elements defined, return as is
                return df
            
            # Generate descriptions using dynamic system
            df['enhanced_description'] = df.apply(
                lambda row: self._generate_dynamic_description(description_elements, row),
                axis=1
            )
            
            # Update column mapping to use enhanced descriptions
            column_mapping['Body (HTML)'] = 'enhanced_description'
            
            return df
            
        except Exception as e:
            st.warning(f"Description generation failed: {str(e)}. Using empty descriptions.")
            df['enhanced_description'] = ""
            return df
    
    def _generate_dynamic_description(self, description_elements: list, row: pd.Series) -> str:
        """Generate description with proper HTML tag application and NO DECIMALS"""
        try:
            # Sort elements by order
            sorted_elements = sorted([elem for elem in description_elements if elem.get('column')], 
                                key=lambda x: x.get('order', 0))
            
            html_parts = []
            
            for element in sorted_elements:
                column = element.get('column', '')
                label = element.get('label', '')
                html_tag = element.get('html_tag', 'p')
                
                if column and column in row.index:
                    value = self._clean_value_no_decimals(row[column], column)
                    if value:
                        # Format with proper HTML structure
                        if label and label.strip():
                            # Label exists - apply HTML tag to label only
                            if html_tag == 'none':
                                # No tags - plain text label with value in <p>
                                html_parts.append(f"{label}: <p>{value}</p>")
                            elif html_tag == 'br':
                                # Label with line break, value in <p>
                                html_parts.append(f"{label}:<br><p>{value}</p>")
                            elif html_tag == 'li':
                                # List item - strong label, value in <p>
                                html_parts.append(f"<li><strong>{label}:</strong> <p>{value}</p></li>")
                            else:
                                # Apply tag to label only (h3, h4, strong, etc.), value in <p>
                                html_parts.append(f"<{html_tag}>{label}:</{html_tag}><p>{value}</p>")
                        else:
                            # No label - just value in <p>
                            html_parts.append(f"<p>{value}</p>")
            
            return "".join(html_parts) if html_parts else ""
            
        except Exception as e:
            return ""
    
    def _format_with_proper_html_tags(self, label: str, value: str, html_tag: str) -> str:
        """Apply HTML tag only to label, keep value in <p> tag"""
        if not label or not label.strip():
            # No label, just return value in <p> tag
            return f"<p>{value}</p>"
        
        # Apply HTML tag to label only
        if html_tag == 'none':
            formatted_label = label
        elif html_tag == 'br':
            formatted_label = f"{label}<br>"
        elif html_tag == 'li':
            # For list items, wrap the whole thing
            return f"<li><strong>{label}:</strong> {value}</li>"
        else:
            # Apply tag to label with colon
            formatted_label = f"<{html_tag}>{label}:</{html_tag}>"
        
        # Value always in <p> tag
        return f"{formatted_label}<p>{value}</p>"
    
    def _clean_value_no_decimals(self, value, column_name: str = '') -> str:
        """FIXED: Remove decimals from ALL numeric values that should be integers"""
        if pd.isna(value) or str(value).strip() == '':
            return ""
        
        # Fields that should ALWAYS be integers (no decimals)
        integer_fields = [
            'no of components', 'components', 'number_of_components', 
            'component_count', 'quantity', 'qty', 'count', 'pieces',
            'set', 'items', 'number', 'no'
        ]
        
        column_lower = column_name.lower() if column_name else ''
        should_be_integer = any(field in column_lower for field in integer_fields)
        
        # Try to convert to number and remove decimal if needed
        try:
            num_value = float(str(value).strip())
            # If it's a whole number OR should be integer field, remove decimal
            if should_be_integer or num_value == int(num_value):
                return str(int(num_value))
            else:
                # Keep as is for actual decimal values (like prices)
                return str(value).strip()
        except (ValueError, TypeError):
            # Not a number, return as string
            return str(value).strip()