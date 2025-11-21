# backend/data_processor.py - FIXED: Blank compare price handling + paragraph tag fix
import pandas as pd
import streamlit as st
from helpers.utils import get_column_value, clean_value, sort_sizes_with_quantities

class DataProcessor:
    """Enhanced data processing service with latest Shopify format support"""
    
    def process_data(self, df_raw, column_mapping, config):
        """Main data processing pipeline with enhanced description support"""
        # Step 1: Process variants with inventory
        df_variants = self._process_variants(df_raw, column_mapping, config)
        
        # Step 2: Generate handles
        df_with_handles = self._generate_handles(df_variants, column_mapping)
        
        return df_with_handles
    
    def initialize_variants(self, df, column_mapping, config):
        """FIXED: Initialize variant management with proper default_qty from config"""
        unique_variants = []
        variant_products = {}
        extracted_quantities = {}
        extracted_compare_prices = {}
        
        # FIXED: Get the current default_qty from config (not session state)
        current_default_qty = config.get('default_qty', 10)
        
        for _, row in df.iterrows():
            size = clean_value(row.get('sizes_list', ''))
            color = clean_value(row.get('colours_list', ''))
            title = clean_value(get_column_value(row, column_mapping, 'Title', 'Unknown'))
            
            # Extract quantity from size (e.g., "M-5" means 5 quantity)
            extracted_qty = row.get('extracted_quantity', 0)
            
            # FIXED: Handle blank compare prices properly
            extracted_compare_price = row.get('uploaded_compare_price', None)
            
            variant_key = (size, color, title)
            variant_key_str = f"{size}|{color}|{title}"
            
            if variant_key not in unique_variants:
                unique_variants.append(variant_key)
                variant_products[variant_key] = title
                extracted_quantities[variant_key_str] = extracted_qty
                # FIXED: Store None if no compare price (not default)
                extracted_compare_prices[variant_key_str] = extracted_compare_price
        
        # Store in session state
        st.session_state.unique_variants = unique_variants
        st.session_state.variant_products = variant_products
        
        # FIXED: Initialize quantity mappings with current default_qty from config
        if 'variant_quantities' not in st.session_state:
            st.session_state.variant_quantities = {}
        
        # Update all quantities - use extracted if available, otherwise use current default_qty
        for size, color, title in unique_variants:
            variant_key = f"{size}|{color}|{title}"
            extracted_qty = extracted_quantities.get(variant_key, 0)
            
            # If variant not yet in session, initialize it
            if variant_key not in st.session_state.variant_quantities:
                # Use extracted quantity if > 0, otherwise use current default_qty from config
                st.session_state.variant_quantities[variant_key] = extracted_qty if extracted_qty > 0 else current_default_qty
        
        # FIXED: Initialize compare price mappings - keep blank if source is blank
        if 'variant_compare_prices' not in st.session_state:
            st.session_state.variant_compare_prices = {}
        
        for size, color, title in unique_variants:
            variant_key = f"{size}|{color}|{title}"
            
            # If variant not yet in session, initialize it
            if variant_key not in st.session_state.variant_compare_prices:
                extracted_price = extracted_compare_prices.get(variant_key, None)
                # FIXED: Store None if blank, not default value
                st.session_state.variant_compare_prices[variant_key] = extracted_price
        
        # Store extracted quantities for UI display
        st.session_state.extracted_quantities = extracted_quantities
        st.session_state.extracted_compare_prices = extracted_compare_prices
        
        # IMPORTANT: Store the config default_qty so UI can show it
        st.session_state.config_default_qty = current_default_qty
    
    def generate_shopify_csv(self, df, column_mapping, config):
        """Generate final Shopify CSV with LATEST format including all metafields"""
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
        
        # Create final dataframe with EXACT column order
        shopify_df = pd.DataFrame(grouped_data)
        
        # Reorder columns to match exact Shopify format
        shopify_df = self._reorder_columns_to_shopify_format(shopify_df)
        
        # FIXED: Clean up data - keep blank compare prices as blank
        for col in shopify_df.columns:
            if shopify_df[col].dtype == 'object':
                shopify_df[col] = shopify_df[col].fillna('').astype(str)
                shopify_df[col] = shopify_df[col].replace(['nan', 'NaN', 'None'], '')
            elif col == "Variant Compare At Price":
                # FIXED: Keep None/NaN as empty string for compare price
                shopify_df[col] = shopify_df[col].apply(lambda x: '' if pd.isna(x) or x == 0 else x)
            else:
                shopify_df[col] = shopify_df[col].fillna(0)
        
        return shopify_df
    
    def _reorder_columns_to_shopify_format(self, df):
        """Reorder columns to match exact Shopify format"""
        # Exact column order from Shopify format
        column_order = [
            "Handle", "Title", "Body (HTML)", "Vendor", "Product Category", "Type", "Tags", "Published",
            "Option1 Name", "Option1 Value", "Option1 Linked To",
            "Option2 Name", "Option2 Value", "Option2 Linked To",
            "Option3 Name", "Option3 Value", "Option3 Linked To",
            "Variant SKU", "Variant Grams", "Variant Inventory Tracker", "Variant Inventory Qty",
            "Variant Inventory Policy", "Variant Fulfillment Service", "Variant Price", "Variant Compare At Price",
            "Variant Requires Shipping", "Variant Taxable",
            "Unit Price Total Measure", "Unit Price Total Measure Unit",
            "Unit Price Base Measure", "Unit Price Base Measure Unit",
            "Variant Barcode",
            "Image Src", "Image Position", "Image Alt Text", "Gift Card",
            "SEO Title", "SEO Description",
            "Google Shopping / Google Product Category", "Google Shopping / Gender", "Google Shopping / Age Group",
            "Google Shopping / MPN", "Google Shopping / Condition", "Google Shopping / Custom Product",
            "Google Shopping / Custom Label 0", "Google Shopping / Custom Label 1", "Google Shopping / Custom Label 2",
            "Google Shopping / Custom Label 3", "Google Shopping / Custom Label 4",
            # Metafields
            "Gender (product.metafields.custom.gender)",
            "Google: Custom Product (product.metafields.mm-google-shopping.custom_product)",
            "Age group (product.metafields.shopify.age-group)",
            "Color (product.metafields.shopify.color-pattern)",
            "Dress occasion (product.metafields.shopify.dress-occasion)",
            "Dress style (product.metafields.shopify.dress-style)",
            "Fabric (product.metafields.shopify.fabric)",
            "Neckline (product.metafields.shopify.neckline)",
            "Size (product.metafields.shopify.size)",
            "Skirt/Dress length type (product.metafields.shopify.skirt-dress-length-type)",
            "Sleeve length type (product.metafields.shopify.sleeve-length-type)",
            "Target gender (product.metafields.shopify.target-gender)",
            "Complementary products (product.metafields.shopify--discovery--product_recommendation.complementary_products)",
            "Related products (product.metafields.shopify--discovery--product_recommendation.related_products)",
            "Related products settings (product.metafields.shopify--discovery--product_recommendation.related_products_display)",
            "Search product boosts (product.metafields.shopify--discovery--product_search_boost.queries)",
            "Variant Image", "Variant Weight Unit", "Variant Tax Code", "Cost per item", "Status"
        ]
        
        # Add missing columns with empty values
        for col in column_order:
            if col not in df.columns:
                df[col] = ""
        
        # Return dataframe with exact column order
        return df[column_order]
    
    def _process_variants(self, df_raw, column_mapping, config):
        """Process variants and extract inventory data with enhanced configuration support"""
        df_exploded_list = []
        
        for _, row in df_raw.iterrows():
            # Use both old and new field names for compatibility
            sizes_value = (get_column_value(row, column_mapping, 'Option1 Value', '') or 
                          get_column_value(row, column_mapping, 'size', ''))
            colours_value = (get_column_value(row, column_mapping, 'Option2 Value', '') or 
                           get_column_value(row, column_mapping, 'colour', ''))
            
            sorted_sizes, size_quantity_map = sort_sizes_with_quantities(clean_value(sizes_value))
            colors = [c.strip() for c in str(clean_value(colours_value)).split(",") if c.strip()]
            
            # FIXED: Extract compare price - handle blank properly
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
                    
                    # FIXED: Store None for blank compare prices
                    new_row["uploaded_compare_price"] = uploaded_compare_price
                    
                    df_exploded_list.append(new_row)
        
        return pd.DataFrame(df_exploded_list)
    
    def _extract_quantity(self, size, size_quantity_map, config):
        """Extract quantity based on configuration settings"""
        if config.get('bulk_qty_mode', False):
            return config.get('bulk_qty', 10)
        
        if config.get('use_expected_qty', True):
            extracted_qty = size_quantity_map.get(size, 0)
            if extracted_qty > 0:
                return extracted_qty
            else:
                return config.get('fallback_qty', config.get('default_qty', 10))
        
        return config.get('default_qty', 10)
    
    def _extract_compare_price(self, row, column_mapping, config):
        """FIXED: Extract compare price - return None for blank values"""
        if config.get('bulk_compare_price_mode', False):
            return config.get('bulk_compare_price', 0.0)
        
        if config.get('use_expected_compare_price', True):
            compare_price_value = get_column_value(row, column_mapping, 'Variant Compare At Price')
            
            # FIXED: Check if value exists and is not blank
            if compare_price_value and pd.notna(compare_price_value) and str(compare_price_value).strip() != '':
                try:
                    numeric_value = float(str(compare_price_value).strip())
                    if numeric_value >= 0:
                        return numeric_value
                except (ValueError, TypeError):
                    pass
            
            # FIXED: Return None for blank, not default
            return None
        
        return config.get('default_compare_price', 0.0)
    
    def _apply_size_surcharges(self, df, column_mapping, config):
        """Apply size-based surcharges to variant prices"""
        if not config.get('enable_surcharge', False):
            return df
        
        def apply_surcharge(row):
            base_price = clean_value(get_column_value(row, column_mapping, 'Variant Price', 0), is_numeric=True)
            
            if base_price <= 0:
                return base_price
            
            size = row.get('display_size', '').strip().upper()
            
            if config.get('bulk_surcharge_mode', False):
                surcharge_percent = config.get('bulk_surcharge_percent', 0) / 100.0
                return base_price * (1 + surcharge_percent)
            else:
                surcharge_rules = config.get('surcharge_rules', {})
                if size in surcharge_rules:
                    surcharge_percent = surcharge_rules[size]
                    return base_price * (1 + surcharge_percent)
            
            return base_price
        
        df['final_variant_price'] = df.apply(apply_surcharge, axis=1)
        return df
    
    def _generate_handles(self, df, column_mapping):
        """Generate Shopify handles"""
        title_series = df.apply(lambda row: get_column_value(row, column_mapping, 'Title', 'Unknown'), axis=1)
        product_code_series = df.apply(lambda row: (get_column_value(row, column_mapping, 'Variant SKU', '') or 
                                                   get_column_value(row, column_mapping, 'product code', '')), axis=1)
        
        df["Handle"] = (title_series.astype(str).fillna("").str.strip() + "-" + 
                        product_code_series.fillna("").astype(str).str.strip())
        
        df["Handle"] = (df["Handle"]
                        .str.replace(r"[^\w\s-]", "", regex=True)
                        .str.replace(r"\s+", "-", regex=True)
                        .str.lower()
                        .str.replace(r"-+", "-", regex=True)
                        .str.strip("-"))
        
        return df
    
    def _apply_variant_mappings(self, df, column_mapping, config):
        """Apply stored quantity and price mappings with enhanced configuration support"""
        title_series = df.apply(lambda row: get_column_value(row, column_mapping, 'Title', 'Unknown'), axis=1)
        df["_variant_key"] = (df["sizes_list"].astype(str).fillna("").str.strip() + "|" + 
                             df["colours_list"].astype(str).fillna("").str.strip() + "|" + 
                             title_series.astype(str).fillna("").str.strip())
        
        # Apply quantity based on configuration
        if config.get('bulk_qty_mode', False):
            bulk_qty = config.get('bulk_qty', 10)
            df["Variant Inventory Qty"] = bulk_qty
        elif 'variant_quantities' in st.session_state:
            def get_quantity(variant_key):
                return st.session_state.variant_quantities.get(variant_key, config.get('default_qty', 10))
            df["Variant Inventory Qty"] = df["_variant_key"].apply(get_quantity)
        else:
            df["Variant Inventory Qty"] = df.apply(
                lambda row: row.get('extracted_quantity', config.get('default_qty', 10)), axis=1
            )
        
        # FIXED: Apply compare price - keep None for blank values
        if config.get('bulk_compare_price_mode', False):
            bulk_compare_price = config.get('bulk_compare_price', 0.0)
            df["Variant Compare At Price"] = bulk_compare_price
        elif 'variant_compare_prices' in st.session_state:
            def get_compare_price(variant_key):
                price = st.session_state.variant_compare_prices.get(variant_key, None)
                # FIXED: Return None if blank, not default
                return price
            df["Variant Compare At Price"] = df["_variant_key"].apply(get_compare_price)
        else:
            df["Variant Compare At Price"] = df.apply(
                lambda row: row.get('uploaded_compare_price', None), axis=1
            )
        
        df["Variant Inventory Qty"] = pd.to_numeric(df["Variant Inventory Qty"], errors='coerce').fillna(0).astype(int)
        # FIXED: Keep None values as None for compare price
        df["Variant Compare At Price"] = df["Variant Compare At Price"].apply(
            lambda x: None if pd.isna(x) or x == '' else float(x) if x != 0 else None
        )
    
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
        """Create main product row with ALL new Shopify fields and metafields"""
        display_size = clean_value(row.get("display_size", ""))
        has_sizes = bool(display_size)
        has_colors = bool(clean_value(row.get("colours_list", "")))
        
        # Get body HTML - prioritize enhanced description
        body_html = ""
        if 'enhanced_description' in row.index and pd.notna(row['enhanced_description']):
            body_html = str(row['enhanced_description'])
        elif 'enhanced_body' in row.index and pd.notna(row['enhanced_body']):
            body_html = str(row['enhanced_body'])
        else:
            description = clean_value(get_column_value(row, column_mapping, 'Body (HTML)', ''))
            if description:
                body_html = f"<p>{description}</p>"
        
        # Use final price with surcharges if available
        variant_price = row.get('final_variant_price', get_column_value(row, column_mapping, 'Variant Price', 0))
        variant_price = clean_value(variant_price, is_numeric=True)
        
        # FIXED: Handle blank compare prices
        compare_price = row.get("Variant Compare At Price", None)
        if pd.isna(compare_price) or compare_price == '' or compare_price == 0:
            compare_price = ''
        else:
            compare_price = clean_value(compare_price, is_numeric=True)
        
        return {
            # Core Product Fields
            "Handle": clean_value(row.get("Handle", "")),
            "Title": clean_value(get_column_value(row, column_mapping, 'Title', 'Unknown')),
            "Body (HTML)": body_html,
            "Vendor": config.get('vendor_name', 'YourBrandName'),
            "Product Category": clean_value(get_column_value(row, column_mapping, 'Product Category', '')),
            "Type": clean_value(get_column_value(row, column_mapping, 'Type', '')),
            "Tags": clean_value(row.get("ai_tags", "")),
            "Published": "TRUE" if str(clean_value(get_column_value(row, column_mapping, 'published', ''))).lower() == "active" else "FALSE",
            
            # Options with Linked To fields
            "Option1 Name": "Size" if has_sizes else "",
            "Option1 Value": display_size,
            "Option1 Linked To": "",
            "Option2 Name": "Color" if has_colors else "",
            "Option2 Value": clean_value(row.get("colours_list", "")),
            "Option2 Linked To": "",
            "Option3 Name": "",
            "Option3 Value": "",
            "Option3 Linked To": "",
            
            # Variant Fields
            "Variant SKU": clean_value(get_column_value(row, column_mapping, 'Variant SKU', '') or 
                                     get_column_value(row, column_mapping, 'product code', '')),
            "Variant Grams": 0,
            "Variant Inventory Tracker": "",
            "Variant Inventory Qty": clean_value(row.get("Variant Inventory Qty", 0), is_numeric=True),
            "Variant Inventory Policy": config.get('inventory_policy', 'deny'),
            "Variant Fulfillment Service": "manual",
            "Variant Price": variant_price,
            "Variant Compare At Price": compare_price,  # FIXED: Blank if no value
            "Variant Requires Shipping": "TRUE",
            "Variant Taxable": "TRUE",
            
            # Unit Price Fields
            "Unit Price Total Measure": "",
            "Unit Price Total Measure Unit": "",
            "Unit Price Base Measure": "",
            "Unit Price Base Measure Unit": "",
            
            "Variant Barcode": "",
            
            # Image Fields
            "Image Src": "",
            "Image Position": "",
            "Image Alt Text": "",
            "Gift Card": "FALSE",
            
            # SEO Fields
            "SEO Title": "",
            "SEO Description": "",
            
            # Google Shopping Fields
            "Google Shopping / Google Product Category": "",
            "Google Shopping / Gender": "",
            "Google Shopping / Age Group": "",
            "Google Shopping / MPN": "",
            "Google Shopping / Condition": "",
            "Google Shopping / Custom Product": "",
            "Google Shopping / Custom Label 0": "",
            "Google Shopping / Custom Label 1": "",
            "Google Shopping / Custom Label 2": "",
            "Google Shopping / Custom Label 3": "",
            "Google Shopping / Custom Label 4": "",
            
            # Metafields
            "Gender (product.metafields.custom.gender)": "",
            "Google: Custom Product (product.metafields.mm-google-shopping.custom_product)": "",
            "Age group (product.metafields.shopify.age-group)": "",
            "Color (product.metafields.shopify.color-pattern)": "",
            "Dress occasion (product.metafields.shopify.dress-occasion)": "",
            "Dress style (product.metafields.shopify.dress-style)": "",
            "Fabric (product.metafields.shopify.fabric)": "",
            "Neckline (product.metafields.shopify.neckline)": "",
            "Size (product.metafields.shopify.size)": "",
            "Skirt/Dress length type (product.metafields.shopify.skirt-dress-length-type)": "",
            "Sleeve length type (product.metafields.shopify.sleeve-length-type)": "",
            "Target gender (product.metafields.shopify.target-gender)": "",
            "Complementary products (product.metafields.shopify--discovery--product_recommendation.complementary_products)": "",
            "Related products (product.metafields.shopify--discovery--product_recommendation.related_products)": "",
            "Related products settings (product.metafields.shopify--discovery--product_recommendation.related_products_display)": "",
            "Search product boosts (product.metafields.shopify--discovery--product_search_boost.queries)": "",
            
            # Final Fields
            "Variant Image": "",
            "Variant Weight Unit": "",
            "Variant Tax Code": "",
            "Cost per item": 0,
            "Status": "draft"
        }
    
    def _create_variant_row(self, row, column_mapping, handle, config):
        """Create variant row with new fields"""
        display_size = clean_value(row.get("display_size", ""))
        variant_price = row.get('final_variant_price', get_column_value(row, column_mapping, 'Variant Price', 0))
        variant_price = clean_value(variant_price, is_numeric=True)
        
        # FIXED: Handle blank compare prices
        compare_price = row.get("Variant Compare At Price", None)
        if pd.isna(compare_price) or compare_price == '' or compare_price == 0:
            compare_price = ''
        else:
            compare_price = clean_value(compare_price, is_numeric=True)
        
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
            "Option1 Value": display_size,
            "Option1 Linked To": "",
            "Option2 Name": "",
            "Option2 Value": clean_value(row.get("colours_list", "")),
            "Option2 Linked To": "",
            "Option3 Name": "",
            "Option3 Value": "",
            "Option3 Linked To": "",
            "Variant SKU": clean_value(get_column_value(row, column_mapping, 'Variant SKU', '') or get_column_value(row, column_mapping, 'product code', '')),
            "Variant Grams": 0,
            "Variant Inventory Tracker": "",
            "Variant Inventory Qty": clean_value(row.get("Variant Inventory Qty", 0), is_numeric=True),
            "Variant Inventory Policy": config.get('inventory_policy', 'deny'),
            "Variant Fulfillment Service": "manual",
            "Variant Price": variant_price,
            "Variant Compare At Price": compare_price,  # FIXED: Blank if no value
            "Variant Requires Shipping": "TRUE",
            "Variant Taxable": "TRUE",
            "Unit Price Total Measure": "",
            "Unit Price Total Measure Unit": "",
            "Unit Price Base Measure": "",
            "Unit Price Base Measure Unit": "",
            "Variant Barcode": "",
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
            "Google Shopping / Condition": "",
            "Google Shopping / Custom Product": "",
            "Google Shopping / Custom Label 0": "",
            "Google Shopping / Custom Label 1": "",
            "Google Shopping / Custom Label 2": "",
            "Google Shopping / Custom Label 3": "",
            "Google Shopping / Custom Label 4": "",
            "Gender (product.metafields.custom.gender)": "",
            "Google: Custom Product (product.metafields.mm-google-shopping.custom_product)": "",
            "Age group (product.metafields.shopify.age-group)": "",
            "Color (product.metafields.shopify.color-pattern)": "",
            "Dress occasion (product.metafields.shopify.dress-occasion)": "",
            "Dress style (product.metafields.shopify.dress-style)": "",
            "Fabric (product.metafields.shopify.fabric)": "",
            "Neckline (product.metafields.shopify.neckline)": "",
            "Size (product.metafields.shopify.size)": "",
            "Skirt/Dress length type (product.metafields.shopify.skirt-dress-length-type)": "",
            "Sleeve length type (product.metafields.shopify.sleeve-length-type)": "",
            "Target gender (product.metafields.shopify.target-gender)": "",
            "Complementary products (product.metafields.shopify--discovery--product_recommendation.complementary_products)": "",
            "Related products (product.metafields.shopify--discovery--product_recommendation.related_products)": "",
            "Related products settings (product.metafields.shopify--discovery--product_recommendation.related_products_display)": "",
            "Search product boosts (product.metafields.shopify--discovery--product_search_boost.queries)": "",
            "Variant Image": "",
            "Variant Weight Unit": "",
            "Variant Tax Code": "",
            "Cost per item": 0,
            "Status": ""
        }