# helpers/utils.py - CLEANED: Removed all legacy description generation code
import pandas as pd
import numpy as np
import re
from difflib import SequenceMatcher

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

# Core utility functions for column mapping and data cleaning
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
    """Clean values to avoid NaN in output - NO DECIMALS for integers"""
    if pd.isna(value) or value == 'nan' or value == 'NaN' or str(value).strip() == '':
        return default_numeric if is_numeric else ""
    
    if is_numeric:
        try:
            num_value = float(str(value).strip())
            # If it's a whole number, return as integer (no decimal)
            if num_value == int(num_value):
                return int(num_value)
            return num_value
        except (ValueError, TypeError):
            return default_numeric
    
    return str(value).strip()

def safe_get_column_data(df, column_mapping, standard_name, default_value=""):
    """Safely get column data with fallback to direct column access"""
    # Try normalized column mapping first
    actual_column = column_mapping.get(standard_name)
    if actual_column and actual_column in df.columns:
        return df[actual_column]
    
    # Fallback to direct access
    if standard_name in df.columns:
        return df[standard_name]
        
    # Try case-insensitive search
    for col in df.columns:
        if col.lower().strip() == standard_name.lower().strip():
            return df[col]
    
    # Return series of default values
    return pd.Series([default_value] * len(df), index=df.index)

def sort_sizes_with_quantities(sizes_list):
    """Sort sizes and extract quantities - NO DECIMALS"""
    standard_order = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', '2XL', '3XL', '4XL', '5XL']
    
    # Split and clean sizes
    size_strings = [s.strip() for s in str(sizes_list).split(',') if s.strip()]
    
    # Parse each size string to extract size and quantity
    parsed_sizes = []
    size_quantity_map = {}
    
    for size_string in size_strings:
        actual_size, quantity = parse_size_and_quantity(size_string)
        parsed_sizes.append(actual_size)
        size_quantity_map[actual_size] = int(quantity)  # Force integer
    
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
        matched = False
        for idx, std_size in enumerate(standard_order):
            if size.upper() == std_size.upper():
                standard_sizes.append((idx, size))
                matched = True
                break
        
        if not matched:
            if re.match(r'^\d+$', size):
                numeric_sizes.append((int(size), size))
            elif re.match(r'^X\d+', size.upper()):
                numbers = re.findall(r'\d+', size)
                if numbers:
                    numeric_sizes.append((int(numbers[0]), size))
                else:
                    custom_sizes.append(size)
            else:
                custom_sizes.append(size)
    
    # Sort each category
    standard_sizes.sort(key=lambda x: x[0])
    numeric_sizes.sort(key=lambda x: x[0])
    custom_sizes.sort()
    
    # Combine
    sorted_sizes = ([size for _, size in standard_sizes] + 
                   [size for _, size in numeric_sizes] + 
                   custom_sizes)
    
    return sorted_sizes, size_quantity_map

def parse_size_and_quantity(size_string):
    """Parse size string to extract size and quantity - NO DECIMALS"""
    size_string = str(size_string).strip()
    
    if size_string.lower() == 'custom':
        return 'Custom', 0
    
    if '-' in size_string and size_string.count('-') == 1:
        parts = size_string.split('-')
        size_part = parts[0].strip()
        try:
            qty_part = int(float(parts[1].strip()))  # Convert to int, no decimals
            return size_part, qty_part
        except ValueError:
            return size_string, 0
    else:
        return size_string, 0