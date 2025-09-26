# helpers/description_generator.py - Unified description generation supporting both legacy and dynamic systems
import pandas as pd
import streamlit as st
from helpers.utils import clean_value, get_column_value

class DescriptionGenerator:
    """Unified description generator supporting both legacy column descriptions and dynamic description builder"""
    
    def apply_enhanced_descriptions(self, df: pd.DataFrame, column_mapping: dict, column_descriptions: dict) -> pd.DataFrame:
        """Apply enhanced HTML descriptions - now supports both systems"""
        try:
            # Check if we already have dynamic descriptions from the description builder
            if 'enhanced_description' in df.columns:
                # We already have descriptions from the dynamic builder, just update mapping
                column_mapping['Body (HTML)'] = 'enhanced_description'
                return df
            
            # Check if we have description elements from the new system
            description_elements = st.session_state.get('description_elements', [])
            
            if description_elements:
                # Use new dynamic description system
                df['enhanced_description'] = df.apply(
                    lambda row: self._generate_dynamic_description(description_elements, row),
                    axis=1
                )
                column_mapping['Body (HTML)'] = 'enhanced_description'
                return df
            
            # Fall back to legacy system
            df['enhanced_body'] = df.apply(
                lambda row: self._generate_enhanced_body(row, column_mapping, column_descriptions),
                axis=1
            )
            
            # Update column mapping to use enhanced descriptions
            column_mapping['Body (HTML)'] = 'enhanced_body'
            
            return df
            
        except Exception as e:
            st.warning(f"Enhanced description generation failed: {str(e)}. Using standard descriptions.")
            return df
    
    def _generate_dynamic_description(self, description_elements: list, row: pd.Series) -> str:
        """Generate description using the new dynamic description builder"""
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
                    value = clean_value(row[column])
                    if value:
                        # Format content
                        if label and label.strip():
                            content = f"{label}: {value}"
                        else:
                            content = str(value)
                        
                        # Apply HTML tag
                        formatted_content = self._format_with_html_tag(content, html_tag)
                        html_parts.append(formatted_content)
            
            return "".join(html_parts) if html_parts else ""
            
        except Exception as e:
            # Fallback to empty string on error
            return ""
    
    def _generate_enhanced_body(self, row: pd.Series, column_mapping: dict, column_descriptions: dict) -> str:
        """Generate enhanced HTML body for a single product (legacy system)"""
        try:
            html_parts = []
            
            # Start with standard description
            standard_description = self._generate_standard_description(row, column_mapping)
            if standard_description:
                html_parts.append(standard_description)
            
            # Add custom fields and description fields
            custom_content = self._generate_custom_content(row, column_descriptions)
            if custom_content:
                if html_parts:  # Add separator if there's existing content
                    html_parts.append("<hr>")
                html_parts.extend(custom_content)
            
            # Add enhanced mapping fields
            enhanced_content = self._generate_enhanced_mapping_content(row)
            if enhanced_content:
                html_parts.extend(enhanced_content)
            
            return "".join(html_parts) if html_parts else ""
            
        except Exception as e:
            # Fallback to standard description
            return self._generate_standard_description(row, column_mapping)
    
    def _generate_standard_description(self, row: pd.Series, column_mapping: dict) -> str:
        """Generate standard product description HTML (legacy system)"""
        # Main description paragraph
        description = clean_value(get_column_value(row, column_mapping, 'description', ''))
        fabric = clean_value(get_column_value(row, column_mapping, 'fabric', ''))
        celebs_name = clean_value(get_column_value(row, column_mapping, 'celebs name', ''))
        no_of_components = clean_value(get_column_value(row, column_mapping, 'no of components', ''))
        product_code = clean_value(get_column_value(row, column_mapping, 'product code', ''))
        fit = clean_value(get_column_value(row, column_mapping, 'fit', ''))
        sizes_info = clean_value(get_column_value(row, column_mapping, 'sizes info', ''))
        colors = clean_value(get_column_value(row, column_mapping, 'colour', ''))
        delivery_time = clean_value(get_column_value(row, column_mapping, 'delivery time', ''))
        wash_care = clean_value(get_column_value(row, column_mapping, 'wash care', ''))
        technique_used = clean_value(get_column_value(row, column_mapping, 'technique used', ''))
        embroidery_details = clean_value(get_column_value(row, column_mapping, 'embroidery details', ''))

        html_parts = []

        # Description as paragraph
        if description:
            html_parts.append(f"<p>{description}</p>")

        # Product specifications as bullet points
        specs = []
        if fabric: 
            specs.append(f"<li><strong>Fabric</strong>: {fabric}</li>")
        if celebs_name: 
            specs.append(f"<li><strong>Celebrity</strong>: {celebs_name}</li>")
        if no_of_components: 
            specs.append(f"<li><strong>Components</strong>: {no_of_components}</li>")
        if colors: 
            specs.append(f"<li><strong>Color</strong>: {colors}</li>")
        if product_code: 
            specs.append(f"<li><strong>SKU</strong>: {product_code}</li>")
        if fit: 
            specs.append(f"<li><strong>Fit</strong>: {fit}</li>")
        if sizes_info: 
            specs.append(f"<li><strong>Size Info</strong>: {sizes_info}</li>")
        if delivery_time: 
            specs.append(f"<li><strong>Delivery</strong>: {delivery_time}</li>")
        if wash_care: 
            specs.append(f"<li><strong>Care</strong>: {wash_care}</li>")
        if technique_used: 
            specs.append(f"<li><strong>Technique</strong>: {technique_used}</li>")
        if embroidery_details: 
            specs.append(f"<li><strong>Embroidery</strong>: {embroidery_details}</li>")

        if specs:
            html_parts.append("<ul>" + "".join(specs) + "</ul>")

        return "".join(html_parts)
    
    def _generate_custom_content(self, row: pd.Series, column_descriptions: dict) -> list:
        """Generate custom content from column descriptions (legacy system)"""
        if not column_descriptions:
            return []
        
        custom_specs = []
        column_html_tags = st.session_state.get('column_html_tags', {})
        
        for column_name, display_label in column_descriptions.items():
            if column_name in row.index:
                value = clean_value(row[column_name])
                if value and str(value).strip():
                    html_tag = column_html_tags.get(column_name, 'p')
                    content = f"{display_label}: {value}" if display_label != column_name else str(value)
                    formatted_content = self._format_with_html_tag(content, html_tag)
                    custom_specs.append(formatted_content)
        
        return custom_specs
    
    def _generate_enhanced_mapping_content(self, row: pd.Series) -> list:
        """Generate content from enhanced mapping fields (legacy system)"""
        enhanced_mapping = st.session_state.get('enhanced_column_mapping', {})
        column_assignments = st.session_state.get('column_assignments', {})
        column_descriptions = st.session_state.get('column_descriptions', {})
        column_html_tags = st.session_state.get('column_html_tags', {})
        
        if not enhanced_mapping:
            return []
        
        additional_fields = []
        
        for standard_field, actual_column in enhanced_mapping.items():
            # Skip if already handled in descriptions
            if actual_column in column_descriptions:
                continue
            
            # Skip standard Shopify fields (handled elsewhere)
            if standard_field.lower() in ['title', 'vendor', 'product category', 'type', 'published']:
                continue
            
            # Include custom fields
            assignment = column_assignments.get(actual_column, 'ignore')
            if assignment == 'custom_field' and standard_field == actual_column:
                if actual_column in row.index:
                    value = clean_value(row[actual_column])
                    if value and str(value).strip():
                        display_label = actual_column.replace('_', ' ').title()
                        html_tag = column_html_tags.get(actual_column, 'p')
                        content = f"{display_label}: {value}"
                        formatted_content = self._format_with_html_tag(content, html_tag)
                        additional_fields.append(formatted_content)
        
        return additional_fields
    
    def _format_with_html_tag(self, content: str, html_tag: str) -> str:
        """Format content with specified HTML tag"""
        if html_tag == 'none':
            return content
        elif html_tag == 'br':
            return f"{content}<br>"
        elif html_tag == 'li':
            return f"<li>{content}</li>"
        else:
            return f"<{html_tag}>{content}</{html_tag}>"