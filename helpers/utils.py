# helpers/utils.py - Enhanced utility functions with HTML tag support and custom field fixes
import pandas as pd
import numpy as np
import re
import streamlit as st
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

def intelligent_column_mapper(df):
    """
    Enhanced column mapping that uses multiple detection methods
    Returns: (column_mapping, unmapped_columns, confidence_scores)
    """
    # Step 1: Use existing exact matching
    column_mapping = normalize_column_names(df)
    
    # Step 2: Find unmapped columns
    mapped_columns = set(column_mapping.values())
    unmapped_columns = [col for col in df.columns if col not in mapped_columns]
    
    # Step 3: Try fuzzy matching for unmapped columns
    fuzzy_mappings, fuzzy_confidence = fuzzy_match_columns(unmapped_columns, column_mapping)
    
    # Step 4: Try content analysis for remaining unmapped columns
    remaining_unmapped = [col for col in unmapped_columns if col not in fuzzy_mappings.values()]
    content_mappings, content_confidence = analyze_column_content(df, remaining_unmapped, column_mapping)
    
    # Step 5: Combine all mappings with confidence scores
    enhanced_mapping = column_mapping.copy()
    enhanced_mapping.update(fuzzy_mappings)
    enhanced_mapping.update(content_mappings)
    
    # Calculate confidence scores for all mappings
    confidence_scores = {}
    for standard_name, actual_column in column_mapping.items():
        confidence_scores[actual_column] = 1.0  # Exact matches get 100% confidence
    confidence_scores.update(fuzzy_confidence)
    confidence_scores.update(content_confidence)
    
    # Final unmapped columns
    final_unmapped = [col for col in df.columns if col not in enhanced_mapping.values()]
    
    return enhanced_mapping, final_unmapped, confidence_scores

def fuzzy_match_columns(unmapped_columns, existing_mapping):
    """Use fuzzy string matching to find similar column names"""
    # Define column name variations
    COLUMN_MAPPING_VARIANTS = {
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
        'variant compare at price': ['variant compare at price', 'variant_compare_at_price', 'compare_price', 'compare price'],
        'celebs name': ['celebs name', 'celebs_name', 'celebrity_name', 'celebrity name'],
        'fit': ['fit', 'fitting', 'size_fit', 'size fit'],
        'sizes info': ['sizes info', 'sizes_info', 'size_info', 'size info'],
        'delivery time': ['delivery time', 'delivery_time', 'shipping_time', 'shipping time'],
        'wash care': ['wash care', 'wash_care', 'care_instructions', 'care instructions'],
        'technique used': ['technique used', 'technique_used', 'manufacturing_technique'],
        'embroidery details': ['embroidery details', 'embroidery_details', 'embroidery']
    }
    
    fuzzy_mappings = {}
    confidence_scores = {}
    
    for unmapped_col in unmapped_columns:
        best_match = None
        best_score = 0
        best_standard_name = None
        
        # Compare against all possible variants of standard names
        for standard_name, variants in COLUMN_MAPPING_VARIANTS.items():
            # Skip if already mapped
            if standard_name in existing_mapping:
                continue
                
            for variant in variants:
                similarity = calculate_similarity(unmapped_col.lower(), variant.lower())
                if similarity > best_score and similarity > 0.7:  # 70% threshold
                    best_score = similarity
                    best_match = unmapped_col
                    best_standard_name = standard_name
        
        if best_match and best_standard_name:
            fuzzy_mappings[best_standard_name] = best_match
            confidence_scores[best_match] = best_score
    
    return fuzzy_mappings, confidence_scores

def calculate_similarity(str1, str2):
    """Calculate similarity between two strings"""
    # Remove common separators for better matching
    str1_clean = re.sub(r'[_\-\s]+', '', str1)
    str2_clean = re.sub(r'[_\-\s]+', '', str2)
    
    # Use sequence matcher
    similarity = SequenceMatcher(None, str1_clean, str2_clean).ratio()
    
    # Boost score if one string contains the other
    if str2_clean in str1_clean or str1_clean in str2_clean:
        similarity = max(similarity, 0.8)
    
    return similarity

def analyze_column_content(df, unmapped_columns, existing_mapping):
    """Analyze actual data content to guess column purpose"""
    content_mappings = {}
    confidence_scores = {}
    
    for col in unmapped_columns:
        if col not in df.columns:
            continue
            
        # Get sample of non-null values
        sample_values = df[col].dropna().astype(str).head(10).tolist()
        if not sample_values:
            continue
        
        detected_type, confidence = detect_column_type(sample_values, col)
        
        if detected_type and confidence > 0.6:  # 60% threshold for content analysis
            # Make sure we don't overwrite existing mappings
            if detected_type not in existing_mapping:
                content_mappings[detected_type] = col
                confidence_scores[col] = confidence
    
    return content_mappings, confidence_scores

def detect_column_type(sample_values, column_name):
    """Detect what type of data a column contains based on sample values"""
    # Convert to lowercase for analysis
    values_lower = [str(v).lower().strip() for v in sample_values if str(v).strip()]
    column_lower = column_name.lower()
    
    # Price detection
    if detect_prices(values_lower) > 0.7:
        return 'variant price', 0.8
    
    # Status/Published detection
    if detect_status_values(values_lower) > 0.6:
        return 'published', 0.7
    
    # Size detection
    if detect_sizes(values_lower) > 0.6:
        return 'size', 0.7
    
    # Color detection
    if detect_colors(values_lower) > 0.6:
        return 'colour', 0.7
    
    # Category detection (based on common category words)
    if detect_categories(values_lower) > 0.5:
        return 'product category', 0.6
    
    # SKU/Code detection
    if detect_codes(values_lower, column_lower) > 0.7:
        return 'product code', 0.8
    
    return None, 0

def detect_prices(values):
    """Detect if values look like prices"""
    price_indicators = 0
    total_values = len(values)
    
    if total_values == 0:
        return 0
    
    for value in values:
        # Remove common currency symbols and spaces
        clean_value = re.sub(r'[₹$€£,\s]', '', str(value))
        
        # Check if it's a number
        try:
            num = float(clean_value)
            if 0 < num < 100000:  # Reasonable price range
                price_indicators += 1
        except ValueError:
            continue
    
    return price_indicators / total_values

def detect_status_values(values):
    """Detect status/published values"""
    status_words = {'active', 'inactive', 'draft', 'published', 'unpublished', 'true', 'false', 'yes', 'no'}
    status_count = 0
    
    for value in values:
        if str(value).lower().strip() in status_words:
            status_count += 1
    
    return status_count / len(values) if values else 0

def detect_sizes(values):
    """Detect size values"""
    size_patterns = [
        r'\b(xs|s|m|l|xl|xxl|xxxl)\b',  # Standard sizes
        r'\b\d{1,2}\b',  # Numeric sizes
        r'\b(small|medium|large)\b',  # Word sizes
        r'\b\d{1,2}-\d+\b'  # Size with quantity (like "M-10")
    ]
    
    size_count = 0
    for value in values:
        value_str = str(value).lower()
        for pattern in size_patterns:
            if re.search(pattern, value_str):
                size_count += 1
                break
    
    return size_count / len(values) if values else 0

def detect_colors(values):
    """Detect color values"""
    color_words = {
        'red', 'blue', 'green', 'yellow', 'black', 'white', 'pink', 'purple', 
        'orange', 'brown', 'gray', 'grey', 'navy', 'maroon', 'teal', 'cyan',
        'magenta', 'lime', 'olive', 'silver', 'gold', 'beige', 'cream', 'tan'
    }
    
    color_count = 0
    for value in values:
        value_lower = str(value).lower()
        # Check for color words or hex codes
        if any(color in value_lower for color in color_words) or re.search(r'#[0-9a-f]{6}', value_lower):
            color_count += 1
    
    return color_count / len(values) if values else 0

def detect_categories(values):
    """Detect product category values"""
    category_words = {
        'shirt', 'dress', 'pants', 'jeans', 'jacket', 'coat', 'shoes', 'boots',
        'bag', 'purse', 'jewelry', 'ring', 'necklace', 'bracelet', 'watch',
        'hat', 'cap', 'scarf', 'belt', 'top', 'blouse', 'skirt', 'shorts',
        'clothing', 'apparel', 'accessories', 'footwear', 'electronics',
        'home', 'kitchen', 'beauty', 'health', 'sports', 'toys', 'books'
    }
    
    category_count = 0
    for value in values:
        value_lower = str(value).lower()
        if any(cat in value_lower for cat in category_words):
            category_count += 1
    
    return category_count / len(values) if values else 0

def detect_codes(values, column_name):
    """Detect SKU/product codes"""
    code_indicators = 0
    
    # Column name hints
    name_hints = ['sku', 'code', 'id', 'number', 'ref']
    name_bonus = 0.3 if any(hint in column_name for hint in name_hints) else 0
    
    for value in values:
        value_str = str(value).strip()
        
        # Typical SKU patterns: alphanumeric, dashes, underscores
        if re.match(r'^[A-Za-z0-9_-]+$', value_str) and len(value_str) > 2:
            code_indicators += 1
    
    base_score = code_indicators / len(values) if values else 0
    return min(1.0, base_score + name_bonus)

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

def generate_enhanced_body_html(row, column_mapping, enhanced_mapping, column_descriptions):
    """
    FIXED: Generate HTML body with enhanced column mapping support and custom fields
    This includes both standard fields and custom fields added to description
    """
    # Start with standard description
    html_parts = [generate_structured_body_html(row, column_mapping)]
    
    # Get HTML tag preferences from session state
    column_html_tags = st.session_state.get('column_html_tags', {})
    column_assignments = st.session_state.get('column_assignments', {})
    
    # Add custom columns that are marked for description or are custom fields
    if column_descriptions or enhanced_mapping:
        custom_specs = []
        
        # Handle columns marked for description
        for column_name, display_label in column_descriptions.items():
            if column_name in row.index:
                value = clean_value(row[column_name])
                if value:  # Only add if value exists
                    html_tag = column_html_tags.get(column_name, 'p')
                    formatted_content = format_with_html_tag(f"{display_label}: {value}", html_tag)
                    custom_specs.append(formatted_content)
        
        # FIXED: Handle custom fields (columns mapped to themselves)
        for standard_field, actual_column in enhanced_mapping.items():
            assignment = column_assignments.get(actual_column, 'ignore')
            
            # Include custom fields and fields not already in descriptions
            if (assignment == 'custom_field' or 
                (actual_column == standard_field and actual_column not in column_descriptions)):
                
                if actual_column in row.index:
                    value = clean_value(row[actual_column])
                    if value:  # Only add if value exists
                        # Use the column name as label for custom fields
                        display_label = column_descriptions.get(actual_column, actual_column)
                        html_tag = column_html_tags.get(actual_column, 'p')
                        formatted_content = format_with_html_tag(f"{display_label}: {value}", html_tag)
                        custom_specs.append(formatted_content)
        
        if custom_specs:
            html_parts.extend(custom_specs)
    
    return "".join(html_parts)

def format_with_html_tag(content, html_tag):
    """Format content with the specified HTML tag"""
    if html_tag == 'none':
        return content
    elif html_tag == 'br':
        return f"{content}<br>"
    elif html_tag == 'li':
        return f"<li>{content}</li>"
    else:
        return f"<{html_tag}>{content}</{html_tag}>"

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
            elif re.match(r'^X\d+', size.upper()):
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