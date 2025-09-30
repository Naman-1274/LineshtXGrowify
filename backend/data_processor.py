# backend/data_processor.py - Enhanced data processing service with description elements support
import pandas as pd
import streamlit as st
from helpers.utils import get_column_value, clean_value, sort_sizes_with_quantities

class DataProcessor:
    """Enhanced data processing service with dynamic description support"""
    
    def process_data(self, df_raw, column_mapping, config):
        """Main data processing pipeline with enhanced description support"""
        # Step 1: Process variants with inventory
        df_variants = self._process_variants(df_raw, column_mapping, config)
        
        # Step 2: Generate handles
        df_with_handles = self._generate_handles(df_variants, column_mapping)
        
        return df_with_handles
    
    def initialize_variants(self, df, column_mapping, config):
        """Initialize variant management data with extracted quantities from size data"""
        unique_variants = []
        variant_products = {}
        extracted_quantities = {}
        extracted_compare_prices = {}
        
        for _, row in df.iterrows():
            size = clean_value(row.get('sizes_list', ''))
            color = clean_value(row.get('colours_list', ''))
            title = clean_value(get_column_value(row, column_mapping, 'Title', 'Unknown'))
            
            # Extract quantity from size (e.g., "M-5" means 5 quantity)
            extracted_qty = row.get('extracted_quantity', 0)
            
            variant_key = (size, color, title)
            variant_key_str = f"{size}|{color}|{title}"
            
            if variant_key not in unique_variants:
                unique_variants.append(variant_key)
                variant_products[variant_key] = title
                extracted_quantities[variant_key_str] = extracted_qty
                extracted_compare_prices[variant_key_str] = row.get('uploaded_compare_price', config.get('default_compare_price', 0))
        
        # Store in session state
        st.session_state.unique_variants = unique_variants
        st.session_state.variant_products = variant_products
        
        # Initialize quantity mappings with extracted quantities
        if 'variant_quantities' not in st.session_state:
            st.session_state.variant_quantities = {}
            for size, color, title in unique_variants:
                variant_key = f"{size}|{color}|{title}"
                # Use extracted quantity if available, otherwise use config default
                extracted_qty = extracted_quantities.get(variant_key, 0)
                default_qty = config.get('default_qty', 10)
                st.session_state.variant_quantities[variant_key] = extracted_qty if extracted_qty > 0 else default_qty
        
        # Initialize compare price mappings
        if 'variant_compare_prices' not in st.session_state:
            st.session_state.variant_compare_prices = {}
            for size, color, title in unique_variants:
                variant_key = f"{size}|{color}|{title}"
                extracted_price = extracted_compare_prices.get(variant_key, config.get('default_compare_price', 0))
                st.session_state.variant_compare_prices[variant_key] = extracted_price
        
        # Store extracted quantities for UI display
        st.session_state.extracted_quantities = extracted_quantities
    
    def generate_shopify_csv(self, df, column_mapping, config):
        """Generate final Shopify CSV with enhanced configuration support"""
        # Get current config from session state
        current_config = st.session_state.get('config', config)
        
        # Apply size surcharges before other processing
        df = self._apply_size_surcharges(df, column_mapping, current_config)
        
        # Apply variant mappings to dataframe
        self._apply_variant_mappings(df, column_mapping, current_config)
        
        # Generate Shopify format
        grouped_data = []
        
        for handle, group in df.groupby("Handle"):
            sorted_group = self._sort_variants_in_group(group)
            
            for idx, row in enumerate(sorted_group):
                if idx == 0:
                    # Main product row
                    grouped_data.append(self._create_main_product_row(row, column_mapping, current_config))
                else:
                    # Variant rows
                    grouped_data.append(self._create_variant_row(row, column_mapping, handle, current_config))
        
        # Create final dataframe
        shopify_df = pd.DataFrame(grouped_data)
        
        # Clean up data
        for col in shopify_df.columns:
            if shopify_df[col].dtype == 'object':
                shopify_df[col] = shopify_df[col].fillna('').astype(str)
                shopify_df[col] = shopify_df[col].replace(['nan', 'NaN', 'None'], '')
            else:
                shopify_df[col] = shopify_df[col].fillna(0)
        
        return shopify_df
    
    def _process_variants(self, df_raw, column_mapping, config):
        """Process variants and extract inventory data with enhanced configuration support"""
        df_exploded_list = []
        default_compare_price = config.get('default_compare_price', 0)
        
        for _, row in df_raw.iterrows():
            # Use both old and new field names for compatibility
            sizes_value = (get_column_value(row, column_mapping, 'Option1 Value', '') or 
                          get_column_value(row, column_mapping, 'size', ''))
            colours_value = (get_column_value(row, column_mapping, 'Option2 Value', '') or 
                           get_column_value(row, column_mapping, 'colour', ''))
            
            sorted_sizes, size_quantity_map = sort_sizes_with_quantities(clean_value(sizes_value))
            colors = [c.strip() for c in str(clean_value(colours_value)).split(",") if c.strip()]
            
            # Extract compare price based on configuration
            uploaded_compare_price = self._extract_compare_price(row, column_mapping, config)
            
            # Create default entries if no sizes or colors
            if not sorted_sizes:
                sorted_sizes = [""]
                size_quantity_map = {"": 0}
            if not colors:
                colors = [""]
            
            # Create all combinations
            for size in sorted_sizes:
                for color in colors:
                    new_row = row.copy()
                    
                    # For descriptions, only use the size part before '-' (e.g., "M-5" becomes "M")
                    display_size = size.split('-')[0].strip() if size and '-' in size else size
                    new_row["sizes_list"] = size  # Keep full size for inventory
                    new_row["display_size"] = display_size  # Size for descriptions
                    new_row["colours_list"] = color
                    
                    # Extract quantity based on configuration
                    extracted_qty = self._extract_quantity(size, size_quantity_map, config)
                    new_row["extracted_quantity"] = extracted_qty
                    new_row["uploaded_compare_price"] = uploaded_compare_price
                    
                    df_exploded_list.append(new_row)
        
        return pd.DataFrame(df_exploded_list)
    
    def _extract_quantity(self, size, size_quantity_map, config):
        """Extract quantity based on configuration settings"""
        if config.get('bulk_qty_mode', False):
            # Bulk mode overrides everything
            return config.get('bulk_qty', 10)
        
        if config.get('use_expected_qty', True):
            # Use expected quantities from data
            extracted_qty = size_quantity_map.get(size, 0)
            if extracted_qty > 0:
                return extracted_qty
            else:
                # Use fallback quantity
                return config.get('fallback_qty', config.get('default_qty', 10))
        
        # Default quantity
        return config.get('default_qty', 10)
    
    def _extract_compare_price(self, row, column_mapping, config):
        """Extract compare price based on configuration settings"""
        if config.get('bulk_compare_price_mode', False):
            # Bulk mode overrides everything
            return config.get('bulk_compare_price', 0.0)
        
        if config.get('use_expected_compare_price', True):
            # Try to get from data
            compare_price_value = get_column_value(row, column_mapping, 'Variant Compare At Price')
            
            if compare_price_value and pd.notna(compare_price_value):
                try:
                    numeric_value = float(str(compare_price_value).strip())
                    if numeric_value >= 0:
                        return numeric_value
                except (ValueError, TypeError):
                    pass
            
            # Use fallback compare price
            return config.get('fallback_compare_price', config.get('default_compare_price', 0.0))
        
        # Default compare price
        return config.get('default_compare_price', 0.0)
    
    def _apply_size_surcharges(self, df, column_mapping, config):
        """Apply size-based surcharges to variant prices"""
        if not config.get('enable_surcharge', False):
            return df
        
        def apply_surcharge(row):
            base_price = clean_value(get_column_value(row, column_mapping, 'Variant Price', 0), is_numeric=True)
            
            if base_price <= 0:
                return base_price
            
            # Get the display size (without quantity info)
            size = row.get('display_size', '').strip().upper()
            
            if config.get('bulk_surcharge_mode', False):
                # Apply bulk surcharge to all sizes
                surcharge_percent = config.get('bulk_surcharge_percent', 0) / 100.0
                return base_price * (1 + surcharge_percent)
            else:
                # Apply individual size surcharges
                surcharge_rules = config.get('surcharge_rules', {})
                if size in surcharge_rules:
                    surcharge_percent = surcharge_rules[size]
                    return base_price * (1 + surcharge_percent)
            
            return base_price
        
        # Apply surcharges to variant prices
        df['final_variant_price'] = df.apply(apply_surcharge, axis=1)
        
        return df
    
    def _generate_handles(self, df, column_mapping):
        """Generate Shopify handles"""
        title_series = df.apply(lambda row: get_column_value(row, column_mapping, 'Title', 'Unknown'), axis=1)
        product_code_series = df.apply(lambda row: (get_column_value(row, column_mapping, 'Variant SKU', '') or 
                                                   get_column_value(row, column_mapping, 'product code', '')), axis=1)
        
        df["Handle"] = (title_series.astype(str).fillna("").str.strip() + "-" + 
                        product_code_series.fillna("").astype(str).str.strip())
        
        # Clean handles
        df["Handle"] = (df["Handle"]
                        .str.replace(r"[^\w\s-]", "", regex=True)
                        .str.replace(r"\s+", "-", regex=True)
                        .str.lower()
                        .str.replace(r"-+", "-", regex=True)
                        .str.strip("-"))
        
        return df
    
    def _apply_bulk_quantities(self, bulk_qty):
        """Apply bulk quantity to all variants"""
        if 'unique_variants' in st.session_state:
            for size, color, title in st.session_state.unique_variants:
                variant_key = f"{size}|{color}|{title}"
                st.session_state.variant_quantities[variant_key] = bulk_qty
    
    def _apply_bulk_compare_prices(self, bulk_price):
        """Apply bulk compare price to all variants"""
        if 'unique_variants' in st.session_state:
            for size, color, title in st.session_state.unique_variants:
                variant_key = f"{size}|{color}|{title}"
                st.session_state.variant_compare_prices[variant_key] = bulk_price
    
    def _apply_variant_mappings(self, df, column_mapping):
        """Apply stored quantity and price mappings"""
        title_series = df.apply(lambda row: get_column_value(row, column_mapping, 'Title', 'Unknown'), axis=1)
        df["_variant_key"] = (df["sizes_list"].astype(str).fillna("").str.strip() + "|" + 
                             df["colours_list"].astype(str).fillna("").str.strip() + "|" + 
                             title_series.astype(str).fillna("").str.strip())
        
        def get_quantity(variant_key):
            return st.session_state.variant_quantities.get(variant_key, 0)
        
        def get_compare_price(variant_key):
            return st.session_state.variant_compare_prices.get(variant_key, 0)
        
        df["Variant Inventory Qty"] = df["_variant_key"].apply(get_quantity)
        df["Variant Compare At Price"] = df["_variant_key"].apply(get_compare_price)
        
        # Ensure numeric types
        df["Variant Inventory Qty"] = pd.to_numeric(df["Variant Inventory Qty"], errors='coerce').fillna(0).astype(int)
        df["Variant Compare At Price"] = pd.to_numeric(df["Variant Compare At Price"], errors='coerce').fillna(0).astype(float)
    
    def _sort_variants_in_group(self, group):
        """Sort variants within product group"""
        sizes_in_group = group['sizes_list'].unique()
        sorted_sizes_for_group, _ = sort_sizes_with_quantities(','.join(sizes_in_group)) if len(sizes_in_group) > 0 else ([], {})
        
        size_order_map = {size: idx for idx, size in enumerate(sorted_sizes_for_group)}
        
        def sort_key(row):
            size = row['sizes_list']
            color = row['colours_list']
            size_idx = size_order_map.get(size, 999)
            return (size_idx, color)
        
        group_list = list(group.iterrows())
        group_list.sort(key=lambda x: sort_key(x[1]))
        return [row for _, row in group_list]
    
    def _create_main_product_row(self, row, column_mapping, config):
        """Create main product row for Shopify CSV with enhanced configuration support"""
        # Use display_size for size display (without quantity info)
        display_size = clean_value(row.get("display_size", ""))
        has_sizes = bool(display_size)
        has_colors = bool(clean_value(row.get("colours_list", "")))
        
        # Get body HTML - prioritize enhanced description, then enhanced_body, then fallback
        body_html = ""
        
        # First check for dynamic description from description builder
        if 'enhanced_description' in row.index and pd.notna(row['enhanced_description']):
            body_html = str(row['enhanced_description'])
        # Then check for traditional enhanced body
        elif 'enhanced_body' in row.index and pd.notna(row['enhanced_body']):
            body_html = str(row['enhanced_body'])
        else:
            # Fallback to standard description from Body (HTML) mapping
            description = clean_value(get_column_value(row, column_mapping, 'Body (HTML)', ''))
            if description:
                body_html = f"<p>{description}</p>"
        
        # Use final price with surcharges if available, otherwise original price
        variant_price = row.get('final_variant_price', get_column_value(row, column_mapping, 'Variant Price', 0))
        variant_price = clean_value(variant_price, is_numeric=True)
        
        # Handle potential duplicate column usage (columns can be used in both template and descriptions)
        return {
            "Handle": clean_value(row.get("Handle", "")),
            "Title": clean_value(get_column_value(row, column_mapping, 'Title', 'Unknown')),
            "Body (HTML)": body_html,
            "Vendor": config.get('vendor_name', 'YourBrandName'),
            "Product Category": clean_value(get_column_value(row, column_mapping, 'Product Category', '')),
            "Type": clean_value(get_column_value(row, column_mapping, 'Type', '')),
            "Tags": clean_value(row.get("ai_tags", "")),
            "Published": "TRUE" if str(clean_value(get_column_value(row, column_mapping, 'published', ''))).lower() == "active" else "FALSE",
            "Option1 Name": "Size" if has_sizes else "",
            "Option1 Value": display_size,  # Use display size without quantity
            "Option2 Name": "Color" if has_colors else "",
            "Option2 Value": clean_value(row.get("colours_list", "")),
            "Option3 Name": "",
            "Option3 Value": "",
            "Variant SKU": clean_value(get_column_value(row, column_mapping, 'Variant SKU', '') or 
                                     get_column_value(row, column_mapping, 'product code', '')),
            "Variant Grams": 0,
            "Variant Inventory Tracker": "",
            "Variant Inventory Qty": clean_value(row.get("Variant Inventory Qty", 0), is_numeric=True),
            "Variant Inventory Policy": config.get('inventory_policy', 'deny'),
            "Variant Fulfillment Service": "manual",
            "Variant Compare At Price": clean_value(row.get("Variant Compare At Price", 0), is_numeric=True),
            "Variant Price": variant_price,
            "Variant Requires Shipping": "TRUE",
            "Variant Taxable": "TRUE",
            **self._get_empty_shopify_fields()
        }
    
    def _apply_variant_mappings(self, df, column_mapping, config):
        """Apply stored quantity and price mappings with enhanced configuration support"""
        title_series = df.apply(lambda row: get_column_value(row, column_mapping, 'Title', 'Unknown'), axis=1)
        df["_variant_key"] = (df["sizes_list"].astype(str).fillna("").str.strip() + "|" + 
                             df["colours_list"].astype(str).fillna("").str.strip() + "|" + 
                             title_series.astype(str).fillna("").str.strip())
        
        # Apply quantity based on configuration
        if config.get('bulk_qty_mode', False):
            # Bulk quantity mode
            bulk_qty = config.get('bulk_qty', 10)
            df["Variant Inventory Qty"] = bulk_qty
        elif 'variant_quantities' in st.session_state:
            # Use individual variant quantities
            def get_quantity(variant_key):
                return st.session_state.variant_quantities.get(variant_key, config.get('default_qty', 10))
            df["Variant Inventory Qty"] = df["_variant_key"].apply(get_quantity)
        else:
            # Use extracted quantities from data processing
            df["Variant Inventory Qty"] = df.apply(
                lambda row: row.get('extracted_quantity', config.get('default_qty', 10)), axis=1
            )
        
        # Apply compare price based on configuration
        if config.get('bulk_compare_price_mode', False):
            # Bulk compare price mode
            bulk_compare_price = config.get('bulk_compare_price', 0.0)
            df["Variant Compare At Price"] = bulk_compare_price
        elif 'variant_compare_prices' in st.session_state:
            # Use individual variant compare prices
            def get_compare_price(variant_key):
                return st.session_state.variant_compare_prices.get(variant_key, config.get('default_compare_price', 0.0))
            df["Variant Compare At Price"] = df["_variant_key"].apply(get_compare_price)
        else:
            # Use extracted compare prices from data processing
            df["Variant Compare At Price"] = df.apply(
                lambda row: row.get('uploaded_compare_price', config.get('default_compare_price', 0.0)), axis=1
            )
        
        # Ensure numeric types
        df["Variant Inventory Qty"] = pd.to_numeric(df["Variant Inventory Qty"], errors='coerce').fillna(0).astype(int)
        df["Variant Compare At Price"] = pd.to_numeric(df["Variant Compare At Price"], errors='coerce').fillna(0).astype(float)
    
    def _create_variant_row(self, row, column_mapping, handle, config):
        """Create variant row for Shopify CSV with enhanced configuration support"""
        # Use display_size for size display (without quantity info)
        display_size = clean_value(row.get("display_size", ""))
        
        # Use final price with surcharges if available, otherwise original price
        variant_price = row.get('final_variant_price', get_column_value(row, column_mapping, 'Variant Price', 0))
        variant_price = clean_value(variant_price, is_numeric=True)
        
        return {
            "Handle": clean_value(handle),
            "Title": "",
            "Body (HTML)": "",
            "Vendor": "",
            "Product Category": "",
            "Type": "",
            "Tags": "",
            "Published": "",
            "Option1 Name": "",
            "Option1 Value": display_size,  # Use display size without quantity
            "Option2 Name": "",
            "Option2 Value": clean_value(row.get("colours_list", "")),
            "Option3 Name": "",
            "Option3 Value": "",
            "Variant SKU": clean_value(get_column_value(row, column_mapping, 'Variant SKU', '') or 
                                     get_column_value(row, column_mapping, 'product code', '')),
            "Variant Grams": 0,
            "Variant Inventory Tracker": "",
            "Variant Inventory Qty": clean_value(row.get("Variant Inventory Qty", 0), is_numeric=True),
            "Variant Inventory Policy": config.get('inventory_policy', 'deny'),
            "Variant Fulfillment Service": "manual",
            "Variant Compare At Price": clean_value(row.get("Variant Compare At Price", 0), is_numeric=True),
            "Variant Price": variant_price,
            "Variant Requires Shipping": "TRUE",
            "Variant Taxable": "TRUE",
            **self._get_empty_shopify_fields()
        }
    
    def _create_variant_row(self, row, column_mapping, handle, config):
        """Create variant row for Shopify CSV"""
        return {
            "Handle": clean_value(handle),
            "Title": "",
            "Body (HTML)": "",
            "Vendor": "",
            "Product Category": "",
            "Type": "",
            "Tags": "",
            "Published": "",
            "Option1 Name": "",
            "Option1 Value": clean_value(row.get("sizes_list", "")),
            "Option2 Name": "",
            "Option2 Value": clean_value(row.get("colours_list", "")),
            "Option3 Name": "",
            "Option3 Value": "",
            "Variant SKU": clean_value(get_column_value(row, column_mapping, 'Variant SKU', '') or 
                                     get_column_value(row, column_mapping, 'product code', '')),
            "Variant Grams": 0,
            "Variant Inventory Tracker": "",
            "Variant Inventory Qty": clean_value(row.get("Variant Inventory Qty", 0), is_numeric=True),
            "Variant Inventory Policy": config.get('inventory_policy', 'deny'),
            "Variant Fulfillment Service": "manual",
            "Variant Compare At Price": clean_value(row.get("Variant Compare At Price", 0), is_numeric=True),
            "Variant Price": clean_value(get_column_value(row, column_mapping, 'Variant Price', 0), is_numeric=True),
            "Variant Requires Shipping": "TRUE",
            "Variant Taxable": "TRUE",
            **self._get_empty_shopify_fields()
        }
    
    def _get_empty_shopify_fields(self):
        """Get empty Shopify fields"""
        return {
            "Image Src": "",
            "Image Position": "",
            "Image Alt Text": "",
            "Gift Card": "FALSE",
            "SEO Title": "",
            "SEO Description": "",
            "Google Shopping / Google Product Category": "",
            "Google Shopping / Gender": "",
            "Google Shopping / Age Group": "",
            "Google Shopping / MPN": "",
            "Google Shopping / AdWords Grouping": "",
            "Google Shopping / AdWords Labels": "",
            "Google Shopping / Condition": "",
            "Google Shopping / Custom Product": "",
            "Google Shopping / Custom Label 0": "",
            "Google Shopping / Custom Label 1": "",
            "Google Shopping / Custom Label 2": "",
            "Google Shopping / Custom Label 3": "",
            "Google Shopping / Custom Label 4": "",
            "Variant Image": "",
            "Variant Weight Unit": "",
            "Variant Tax Code": "",
            "Cost per item": 0,
            "Status": "draft"
        }