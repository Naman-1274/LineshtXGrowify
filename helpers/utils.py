# helpers/utils.py - Utility functions and data helpers
import pandas as pd
import numpy as np
import re

class FileHandler:
    """Handle file operations"""
    
    @staticmethod
    def load_file(uploaded_file):
        """Load CSV or Excel file"""
        if uploaded_file.name.lower().endswith(".xlsx"):
            return pd.read_excel(uploaded_file)
        else:
            return pd.read_csv(uploaded_file)

class ConfigManager:
    """Manage configuration settings"""
    
    @staticmethod
    def get_default_config():
        """Get default configuration"""
        return {
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

# Core utility functions
def normalize_column_names(df):
    """Normalize column names to handle case sensitivity and common variations"""
    column_mapping = {}
    
    # Define common column name variations (all lowercase for matching)
    column_variants = {
        'title': ['title', 'product_title', 'product title', 'name', 'product_name', 'product name'],
        'description': ['description', 'product_description', 'product description', 'desc'],
        'colour': ['colour', 'color', 'colors', 'colours'],
        'product code': ['product code', 'product_code', 'sku', 'product_sku', 'item_code', 'item code'],
        'product category': ['product category', 'product_category', 'category', 'product_type'],
        'type': ['type', 'product_type', 'product type'],
        'published': ['published', 'status', 'active', 'publish_status', 'publish status'],
        'size': ['size', 'sizes', 'variant_size', 'variant size'],
        'no of components': ['no of components', 'no_of_components', 'components', 'number_of_components', 'component_count'],
        'fabric': ['fabric', 'material', 'fabric_type', 'fabric type'],
        'variant price': ['variant price', 'variant_price', 'price', 'unit_price', 'unit price', 'cost'],
        'variant compare at price': ['variant compare at price', 'variant_compare_at_price', 'compare_price', 'compare price', 'compare at price', 'compare_at_price', 'original_price', 'original price'],
        'celebs name': ['celebs name', 'celebs_name', 'celebrity_name', 'celebrity name', 'celeb_name', 'celeb name'],
        'fit': ['fit', 'fitting', 'size_fit', 'size fit'],
        'sizes info': ['sizes info', 'sizes_info', 'size_info', 'size info'],
        'delivery time': ['delivery time', 'delivery_time', 'shipping_time', 'shipping time'],
        'wash care': ['wash care', 'wash_care', 'care_instructions', 'care instructions'],
        'technique used': ['technique used', 'technique_used', 'manufacturing_technique', 'manufacturing technique'],
        'embroidery details': ['embroidery details', 'embroidery_details', 'embroidery', 'embroidery_info']
    }
    
    # Create lowercase version of actual column names for matching
    actual_columns_lower = {col.lower().strip(): col for col in df.columns}
    
    # Map standardized names to actual column names
    for standard_name, variants in column_variants.items():
        for variant in variants:
            if variant.lower() in actual_columns_lower:
                column_mapping[standard_name] = actual_columns_lower[variant.lower()]
                break
    
    return column_mapping

def get_column_value(row, column_mapping, standard_name, default=""):
    """Get value from row using standardized column names"""
    actual_column = column_mapping.get(standard_name)
    if actual_column and actual_column in row.index:
        return row[actual_column]
    return default

def clean_value(value, is_numeric=False, default_numeric=0):
    """Clean values to avoid NaN in output - case insensitive"""
    if pd.isna(value) or value == 'nan' or value == 'NaN' or str(value).strip() == '':
        return default_numeric if is_numeric else ""
    
    if is_numeric:
        try:
            return float(str(value).strip())
        except (ValueError, TypeError):
            return default_numeric
    
    return str(value).strip()

def safe_get_column_data(df, column_mapping, standard_name, default_value=""):
    """Safely get column data with fallback to direct column access"""
    # Try normalized column mapping first
    actual_column = column_mapping.get(standard_name)
    if actual_column and actual_column in df.columns:
        return df[actual_column]
    
    # Fallback to direct access for backward compatibility
    if standard_name in df.columns:
        return df[standard_name]
        
    # Try case-insensitive search
    for col in df.columns:
        if col.lower().strip() == standard_name.lower().strip():
            return df[col]
    
    # Return series of default values
    return pd.Series([default_value] * len(df), index=df.index)

def parse_size_and_quantity(size_string):
    """Parse size string to extract size and quantity"""
    size_string = str(size_string).strip()
    
    # Handle special cases (case insensitive)
    if size_string.lower() == 'custom':
        return 'Custom', 0
    
    if '-' in size_string and size_string.count('-') == 1:
        parts = size_string.split('-')
        size_part = parts[0].strip()
        try:
            qty_part = int(parts[1].strip())
            return size_part, qty_part
        except ValueError:
            # If second part is not a number, treat whole thing as size
            return size_string, 0
    else:
        # No dash or multiple dashes, treat as size only
        return size_string, 0

def sort_sizes_with_quantities(sizes_list):
    """Sort sizes and extract quantities"""
    standard_order = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', '2XL', '3XL', '4XL', '5XL']
    
    # Split and clean sizes
    size_strings = [s.strip() for s in str(sizes_list).split(',') if s.strip()]
    
    # Parse each size string to extract size and quantity
    parsed_sizes = []
    size_quantity_map = {}
    
    for size_string in size_strings:
        actual_size, quantity = parse_size_and_quantity(size_string)
        parsed_sizes.append(actual_size)
        size_quantity_map[actual_size] = quantity
    
    # Remove duplicates while preserving order
    unique_sizes = []
    seen = set()
    for size in parsed_sizes:
        if size not in seen:
            unique_sizes.append(size)
            seen.add(size)
    
    # Separate standard, numeric, and custom sizes
    standard_sizes = []
    numeric_sizes = []
    custom_sizes = []
    
    for size in unique_sizes:
        # Check if size matches any standard size (case insensitive)
        matched = False
        for idx, std_size in enumerate(standard_order):
            if size.upper() == std_size.upper():
                standard_sizes.append((idx, size))
                matched = True
                break
        
        if not matched:
            # Check if it's a pure numeric size
            if re.match(r'^\d+$', size):
                # Pure numeric size like "5", "10", "12"
                numeric_sizes.append((int(size), size))
            elif re.match(r'^X\d+$', size.upper()):
                # Sizes like "X10", "X20"
                numbers = re.findall(r'\d+', size)
                if numbers:
                    numeric_sizes.append((int(numbers[0]), size))
                else:
                    custom_sizes.append(size)
            else:
                # Other custom sizes
                custom_sizes.append(size)
    
    # Sort each category
    standard_sizes.sort(key=lambda x: x[0])
    numeric_sizes.sort(key=lambda x: x[0])  # Sort numerically
    custom_sizes.sort()
    
    # Combine: standard sizes first, then numeric sizes, then custom sizes
    sorted_sizes = ([size for _, size in standard_sizes] + 
                   [size for _, size in numeric_sizes] + 
                   custom_sizes)
    
    return sorted_sizes, size_quantity_map

def sort_sizes(sizes_list):
    """Legacy function - now just returns the sorted sizes without quantities"""
    sorted_sizes, _ = sort_sizes_with_quantities(sizes_list)
    return sorted_sizes

def generate_structured_body_html(row, column_mapping):
    """Generate HTML body using normalized column access"""
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

    # Other specs as bullet points
    specs = []
    if fabric: 
        specs.append(f"<li><strong>Fabric</strong>: {fabric}</li>")
    if celebs_name: 
        specs.append(f"<li><strong>Celebs Name</strong>: {celebs_name}</li>")
    if no_of_components: 
        specs.append(f"<li><strong>No of components (set)</strong>: {no_of_components}</li>")
    if colors: 
        specs.append(f"<li><strong>Color</strong>: {colors}</li>")
    if product_code: 
        specs.append(f"<li><strong>SKU</strong>: {product_code}</li>")
    if fit: 
        specs.append(f"<li><strong>Fit</strong>: {fit}</li>")
    if sizes_info: 
        specs.append(f"<li><strong>Sizes (surcharges if any)</strong>: {sizes_info}</li>")
    if delivery_time: 
        specs.append(f"<li><strong>Delivery Time</strong>: {delivery_time}</li>")
    if wash_care: 
        specs.append(f"<li><strong>Wash Care</strong>: {wash_care}</li>")
    if technique_used: 
        specs.append(f"<li><strong>Technique Used</strong>: {technique_used}</li>")
    if embroidery_details: 
        specs.append(f"<li><strong>Embroidery Details</strong>: {embroidery_details}</li>")

    if specs:
        html_parts.append("<ul>" + "".join(specs) + "</ul>")

    return "".join(html_parts) if html_parts else ""