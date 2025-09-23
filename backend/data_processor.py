# backend/data_processor.py - Core data processing logic with real-time updates
import pandas as pd
import streamlit as st
import numpy as np
import config
from helpers.utils import (
    normalize_column_names, get_column_value, clean_value,
    sort_sizes_with_quantities, safe_get_column_data
)

class DataProcessor:
    def __init__(self):
        self.column_mapping = {}
    
    def normalize_column_names(self, df):
        """Normalize column names for case-insensitive processing"""
        return normalize_column_names(df)
    
    def process_variants_with_inventory(self, df_raw, column_mapping, config):
        """Process variants and extract inventory quantities and compare prices"""
        df_exploded_list = []
        default_compare_price = config.get('default_compare_price', 0)
        
        for _, row in df_raw.iterrows():
            # Parse sizes and extract quantities
            sizes_value = get_column_value(row, column_mapping, 'size', "")
            colours_value = get_column_value(row, column_mapping, 'colour', "")
            
            sorted_sizes, size_quantity_map = sort_sizes_with_quantities(clean_value(sizes_value))
            colors = [c.strip() for c in str(clean_value(colours_value)).split(",") if c.strip()]
            
            # Extract compare price from uploaded data
            uploaded_compare_price = default_compare_price
            compare_price_value = get_column_value(row, column_mapping, 'variant compare at price')
            
            if compare_price_value and pd.notna(compare_price_value) and str(compare_price_value).strip() != '':
                try:
                    numeric_value = float(str(compare_price_value).strip())
                    if numeric_value >= 0:
                        uploaded_compare_price = numeric_value
                except (ValueError, TypeError):
                    pass
            
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
                    new_row["sizes_list"] = size
                    new_row["colours_list"] = color
                    new_row["extracted_quantity"] = size_quantity_map.get(size, 0)
                    new_row["uploaded_compare_price"] = uploaded_compare_price
                    df_exploded_list.append(new_row)
        
        return pd.DataFrame(df_exploded_list)
    
    def generate_handles(self, df, column_mapping):
        """Generate Shopify handles from title and SKU"""
        title_series = safe_get_column_data(df, column_mapping, 'title', 'Unknown')
        product_code_series = safe_get_column_data(df, column_mapping, 'product code', '')
        
        # Generate handles based on title + SKU combination
        df["Handle"] = (title_series.astype(str).fillna("").str.strip() + "-" + 
                        product_code_series.fillna("").astype(str).str.strip())
        
        # Clean handles for Shopify format
        df["Handle"] = (df["Handle"]
                        .str.replace(r"[^\w\s-]", "", regex=True)
                        .str.replace(r"\s+", "-", regex=True)
                        .str.lower()
                        .str.replace(r"-+", "-", regex=True)
                        .str.strip("-"))
        
        return df
    
    def initialize_variant_management(self, df, column_mapping, config):
        """Initialize variant management data structures"""
        unique_variants = []
        variant_products = {}
        extracted_quantities = {}
        extracted_compare_prices = {}
        
        # Group by handle first, then get variants
        for handle, group in df.groupby("Handle"):
            first_row = group.iloc[0]
            title = clean_value(get_column_value(first_row, column_mapping, 'title', 'Unknown'))
            
            for _, row in group.iterrows():
                size = clean_value(row['sizes_list'])
                color = clean_value(row['colours_list'])
                extracted_qty = row.get('extracted_quantity', 0)
                extracted_compare_price = row.get('uploaded_compare_price', config.get('default_compare_price', 0))
                
                variant_key = (size, color, title)
                if variant_key not in unique_variants:
                    unique_variants.append(variant_key)
                    variant_products[variant_key] = title
                    extracted_quantities[variant_key] = extracted_qty
                    extracted_compare_prices[variant_key] = extracted_compare_price
        
        # Store in session state
        st.session_state.unique_variants = unique_variants
        st.session_state.variant_products = variant_products
        st.session_state.extracted_quantities = extracted_quantities
        st.session_state.extracted_compare_prices = extracted_compare_prices
        st.session_state.unique_variants_processed = True
        
        # Initialize quantity and price mappings
        if 'variant_quantities' not in st.session_state:
            st.session_state.variant_quantities = {}
            for size, color, title in unique_variants:
                variant_key = f"{size}|{color}|{title}"
                extracted_qty = extracted_quantities.get((size, color, title), 0)
                default_qty = config.get('default_qty', 10)
                st.session_state.variant_quantities[variant_key] = extracted_qty if extracted_qty > 0 else default_qty
        
        if 'variant_compare_prices' not in st.session_state:
            st.session_state.variant_compare_prices = {}
            for size, color, title in unique_variants:
                variant_key = f"{size}|{color}|{title}"
                extracted_compare_price = extracted_compare_prices.get((size, color, title), config.get('default_compare_price', 0))
                st.session_state.variant_compare_prices[variant_key] = extracted_compare_price
    
    def apply_bulk_quantities(self, bulk_qty):
        """Apply bulk quantity to all variants"""
        if 'unique_variants' in st.session_state:
            for size, color, title in st.session_state.unique_variants:
                variant_key = f"{size}|{color}|{title}"
                st.session_state.variant_quantities[variant_key] = bulk_qty
    
    def apply_bulk_compare_prices(self, bulk_compare_price):
        """Apply bulk compare price to all variants"""
        if 'unique_variants' in st.session_state:
            for size, color, title in st.session_state.unique_variants:
                variant_key = f"{size}|{color}|{title}"
                st.session_state.variant_compare_prices[variant_key] = bulk_compare_price
    
    def apply_size_surcharges(self, df, column_mapping, surcharge_rules, enable_surcharge):
        """Apply size-based price surcharges"""
        if not enable_surcharge or not surcharge_rules:
            return df
        
        for _, row in df.iterrows():
            size = str(row["sizes_list"]).upper().strip()
            if size in surcharge_rules:
                variant_key = f"{row['sizes_list']}|{row['colours_list']}|{get_column_value(row, column_mapping, 'title', 'Unknown')}"
                
                try:
                    base_price = float(get_column_value(row, column_mapping, 'variant price', 0))
                    new_compare_price = round(base_price * (1 + surcharge_rules[size]), 2)
                    st.session_state.variant_compare_prices[variant_key] = new_compare_price
                except (ValueError, TypeError):
                    continue
        
        return df
    
    def generate_shopify_csv(self, df, column_mapping, config):
        """Generate the final Shopify-compatible CSV structure with real-time config updates"""
        # CRITICAL FIX: Get current config from session state if available
        current_config = st.session_state.get('config', config)
        
        # Apply any real-time config changes
        if current_config.get('bulk_qty_mode'):
            self.apply_bulk_quantities(current_config['bulk_qty'])
        
        if current_config.get('bulk_compare_price_mode'):
            self.apply_bulk_compare_prices(current_config['bulk_compare_price'])
        
        # Apply size surcharges with current config
        if current_config.get('enable_surcharge', False):
            df = self.apply_size_surcharges(df, column_mapping, 
                                          current_config.get('surcharge_rules', {}), 
                                          current_config.get('enable_surcharge', False))
        
        # Apply quantities and compare prices to dataframe
        self._apply_variant_mappings(df, column_mapping)
        
        # Generate the Shopify format
        grouped_data = []
        
        for handle, group in df.groupby("Handle"):
            # Sort variants within each product
            sorted_group = self._sort_variants_in_group(group)
            
            # Create product rows (first row as main product, rest as variants)
            for idx, row in enumerate(sorted_group):
                if idx == 0:
                    # Main product row with current config
                    grouped_data.append(self._create_main_product_row(row, column_mapping, current_config))
                else:
                    # Variant rows with current config
                    grouped_data.append(self._create_variant_row(row, column_mapping, handle, current_config))
        
        # Create final dataframe
        shopify_df = pd.DataFrame(grouped_data)
        
        # Final cleanup
        for col in shopify_df.columns:
            if shopify_df[col].dtype == 'object':
                shopify_df[col] = shopify_df[col].fillna('').astype(str)
                shopify_df[col] = shopify_df[col].replace(['nan', 'NaN', 'None'], '')
            else:
                shopify_df[col] = shopify_df[col].fillna(0)
        
        return shopify_df
    
    def _apply_variant_mappings(self, df, column_mapping):
        """Apply stored quantity and price mappings to the dataframe"""
        # Create variant keys for mapping
        title_series = safe_get_column_data(df, column_mapping, 'title', 'Unknown')
        df["_variant_key"] = (df["sizes_list"].astype(str).fillna("").str.strip() + "|" + 
                             df["colours_list"].astype(str).fillna("").str.strip() + "|" + 
                             title_series.astype(str).fillna("").str.strip())
        
        # Apply quantities with real-time updates
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
        """Sort variants within a product group by size order"""
        from helpers.utils import sort_sizes
        
        sizes_in_group = group['sizes_list'].unique()
        sorted_sizes_for_group = sort_sizes(','.join(sizes_in_group)) if len(sizes_in_group) > 0 else []
        
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
        """Create the main product row for Shopify CSV with current config"""
        from helpers.utils import generate_structured_body_html
        
        has_sizes = bool(clean_value(row["sizes_list"]))
        has_colors = bool(clean_value(row["colours_list"]))
        
        return {
            "Handle": clean_value(row["Handle"]),
            "Title": clean_value(get_column_value(row, column_mapping, 'title', 'Unknown')),
            "Body (HTML)": generate_structured_body_html(row, column_mapping),
            "Vendor": config.get('vendor_name', 'YourBrandName'),
            "Product Category": clean_value(get_column_value(row, column_mapping, 'product category', '')),
            "Type": clean_value(get_column_value(row, column_mapping, 'type', '')),
            "Tags": clean_value(row.get("ai_tags", "")),
            "Published": "TRUE" if str(clean_value(get_column_value(row, column_mapping, 'published', ''))).lower() == "active" else "FALSE",
            "Option1 Name": "Size" if has_sizes else "",
            "Option1 Value": clean_value(row["sizes_list"]),
            "Option2 Name": "Color" if has_colors else "",
            "Option2 Value": clean_value(row["colours_list"]),
            "Option3 Name": "",
            "Option3 Value": "",
            "Variant SKU": f"{clean_value(get_column_value(row, column_mapping, 'product code', ''))}",
            "Variant Grams": 0,
            "Variant Inventory Tracker": "",
            "Variant Inventory Qty": clean_value(row["Variant Inventory Qty"], is_numeric=True),
            "Variant Inventory Policy": config.get('inventory_policy', 'deny'),
            "Variant Fulfillment Service": "manual",
            "Variant Compare At Price": clean_value(row["Variant Compare At Price"], is_numeric=True),
            "Variant Price": clean_value(get_column_value(row, column_mapping, 'variant price', 0), is_numeric=True),
            "Variant Requires Shipping": "",
            "Variant Taxable": "",
            **self._get_empty_shopify_fields()
        }
    
    def _create_variant_row(self, row, column_mapping, handle, config):
        """Create variant rows for Shopify CSV with current config"""
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
            "Option1 Value": clean_value(row["sizes_list"]),
            "Option2 Name": "",
            "Option2 Value": clean_value(row["colours_list"]),
            "Option3 Name": "",
            "Option3 Value": "",
            "Variant SKU": f"{clean_value(get_column_value(row, column_mapping, 'product code', ''))}",
            "Variant Grams": 0,
            "Variant Inventory Tracker": "",
            "Variant Inventory Qty": clean_value(row["Variant Inventory Qty"], is_numeric=True),
            "Variant Inventory Policy": config.get('inventory_policy', 'deny'),
            "Variant Fulfillment Service": "manual",
            "Variant Compare At Price": clean_value(row["Variant Compare At Price"], is_numeric=True),
            "Variant Price": clean_value(get_column_value(row, column_mapping, 'variant price', 0), is_numeric=True),
            "Variant Requires Shipping": "",
            "Variant Taxable": "",
            **self._get_empty_shopify_fields()
        }
    
    def _get_empty_shopify_fields(self):
        """Get empty fields required by Shopify CSV format"""
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