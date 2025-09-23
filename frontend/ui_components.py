# frontend/ui_components.py - UI components with real-time updates
import streamlit as st
import pandas as pd
import time
from helpers.utils import get_column_value, clean_value

class UIComponents:
    def __init__(self):
        pass
    
    def apply_custom_css(self):
        """Apply custom CSS styling"""
        st.markdown("""
        <style>
            .main-header {
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                padding: 2rem;
                border-radius: 10px;
                color: white;
                text-align: center;
                margin-bottom: 2rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .step-header {
                background: linear-gradient(45deg, #f093fb 0%, #f5576c 100%);
                padding: 1rem;
                border-radius: 8px;
                color: white;
                margin: 1rem 0;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            .variant-card {
                background: #f8f9fa;
                padding: 1rem;
                border-radius: 8px;
                border-left: 4px solid #28a745;
                margin: 0.5rem 0;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            }
            .stats-box {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 1rem;
                border-radius: 8px;
                text-align: center;
                margin: 0.5rem;
            }
            .ai-status {
                padding: 0.5rem;
                border-radius: 5px;
                margin: 0.5rem 0;
            }
            .ai-enabled { background-color: #d4edda; color: #155724; }
            .ai-disabled { background-color: #f8d7da; color: #721c24; }
            .config-changed {
                background-color: #fff3cd;
                color: #856404;
                padding: 0.5rem;
                border-radius: 5px;
                margin: 0.5rem 0;
                border: 1px solid #ffeaa7;
            }
        </style>
        """, unsafe_allow_html=True)
    
    def render_header(self):
        """Render main application header"""
        st.markdown("""
        <div class="main-header">
            <h1>🛍️ Advanced Shopify CSV Builder</h1>
            <p>Transform your product data into Shopify-ready imports with AI-powered descriptions and smart inventory management</p>
        </div>
        """, unsafe_allow_html=True)
    
    def show_ai_status(self, ai_enabled):
        """Display AI service status"""
        if ai_enabled:
            st.markdown('<div class="ai-status ai-enabled">✅ AI Features Enabled - Gemini 2.5 Flash Ready</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="ai-status ai-disabled">⚠️ AI Features Disabled - Missing GEMINI_API_KEY</div>', unsafe_allow_html=True)
    
    def render_step_header(self, title):
        """Render section header"""
        st.markdown(f'<div class="step-header"><h2>{title}</h2></div>', unsafe_allow_html=True)
    
    def render_sidebar(self, ai_enabled):
        """Render sidebar configuration with real-time change detection"""
        with st.sidebar:
            st.markdown("## ⚙️ Configuration")
            
            # Store previous config to detect changes
            prev_config = st.session_state.get('sidebar_config', {})
            config = {}
            
            # Processing mode selection
            config['mode'] = st.radio(
                "🤖 AI Processing Mode:",
                options=[
                    "Default template (no AI)",
                    "Simple mode (first sentence + tags)",
                    "Full AI mode (custom description + tags)"
                ],
                index=0,
                disabled=not ai_enabled,
                help="Choose how you want to process product descriptions"
            )
            
            st.markdown("---")
            
            # Size surcharge settings
            st.markdown("### ➕ Size Surcharge Settings")
            config['enable_surcharge'] = st.checkbox("Enable Size Surcharge")
            config['surcharge_rules'] = {}
            
            if config['enable_surcharge']:
                st.caption("Add sizes (greater than XL) with surcharge %")
                num_rules = st.number_input("How many size surcharges?", min_value=1, value=1, step=1)
                
                for i in range(num_rules):
                    cols = st.columns([2, 1])
                    with cols[0]:
                        size = st.text_input(f"Size {i+1}", key=f"surcharge_size_{i}").upper().strip()
                    with cols[1]:
                        percent = st.number_input(f"%", min_value=0.0, value=0.0, step=0.5, key=f"surcharge_percent_{i}")
                    
                    if size and percent > 0:
                        config['surcharge_rules'][size] = percent / 100.0
            
            st.markdown("---")
            
            # Brand settings
            st.markdown("### 🏢 Brand Settings")
            config['vendor_name'] = st.text_input("Vendor Name", value="YourBrandName")
            
            # Inventory settings
            st.markdown("### 📦 Inventory Settings")
            config['inventory_policy'] = st.selectbox("Inventory Policy", options=["deny", "continue"], index=0)
            config['default_qty'] = st.number_input("Fallback Quantity", min_value=0, value=10, step=1)
            config['bulk_qty_mode'] = st.checkbox("Override with Bulk Quantity")
            
            if config['bulk_qty_mode']:
                config['bulk_qty'] = st.number_input("Bulk Quantity", min_value=0, value=config['default_qty'], step=1)
            
            # Price settings
            st.markdown("### 💰 Price Settings")
            config['default_compare_price'] = st.number_input("Default Compare At Price", min_value=0.0, value=0.0, step=0.01, format="%.2f")
            config['bulk_compare_price_mode'] = st.checkbox("Enable Bulk Compare Price")
            
            if config['bulk_compare_price_mode']:
                config['bulk_compare_price'] = st.number_input("Bulk Compare Price", min_value=0, value=config['default_compare_price'], step=0.01, format="%.2f")
            
            st.markdown("---")
            
            # REAL-TIME UPDATE DETECTION
            config_changed = self._detect_config_changes(prev_config, config)
            if config_changed and 'processed_data' in st.session_state:
                st.markdown('<div class="config-changed">⚡ Config changed - Preview will update automatically</div>', unsafe_allow_html=True)
            
            # Store current config for next comparison
            st.session_state.sidebar_config = config.copy()
            
            # File format info
            with st.expander("📋 File Format Requirements", expanded=False):
                st.markdown("""
                **Required Columns (case insensitive):**
                - `title` / `Title` / `Product Title` - Product name
                - `description` / `Description` - Product description  
                - `colour` / `Color` / `Colors` - Colors (comma-separated)
                - `product code` / `Product Code` / `SKU` - SKU base
                - `product category` / `Category` - Category
                - `type` / `Type` / `Product Type` - Product type
                - `published` / `Status` - Status (active/inactive)
                - `size` / `Size` / `Sizes` - Size format: `S-4,M-8,L-12,XL-16`
                - `no of components` / `Components` - Number of components/pieces
                - `fabric` / `Fabric` / `Material` - Fabric type/material
                """)
            
            return config
    
    def _detect_config_changes(self, prev_config, current_config):
        """Detect if configuration has changed to trigger real-time updates"""
        if not prev_config:
            return False
        
        # Key settings that affect the final output
        key_settings = [
            'vendor_name', 'inventory_policy', 'bulk_qty_mode', 'bulk_qty',
            'bulk_compare_price_mode', 'bulk_compare_price', 'enable_surcharge',
            'surcharge_rules'
        ]
        
        for setting in key_settings:
            if prev_config.get(setting) != current_config.get(setting):
                return True
    
    def render_file_upload(self):
        """Render file upload section"""
        col1, col2, col3 = st.columns([200, 1, 1])
        
        with col1:
            uploaded_file = st.file_uploader(
                "Choose your CSV or Excel file",
                type=["csv", "xlsx"],
                help="Upload a file containing your product data"
            )
        
        with col2:
            if uploaded_file:
                file_size = len(uploaded_file.getvalue()) / 1024
                st.metric("File Size", f"{file_size:.1f} KB")
        
        with col3:
            if uploaded_file:
                file_type = "Excel" if uploaded_file.name.lower().endswith(".xlsx") else "CSV"
                st.metric("File Type", file_type)
        
        return uploaded_file
    
    def show_file_metrics(self, df_raw, column_mapping):
        """Display file loading metrics"""
        # Calculate metrics
        total_variants = 0
        active_products = 0
        
        for _, row in df_raw.iterrows():
            sizes_value = get_column_value(row, column_mapping, 'size', "")
            colours_value = get_column_value(row, column_mapping, 'colour', "")
            published_value = get_column_value(row, column_mapping, 'published', "")
            
            size_count = len([s.strip() for s in str(sizes_value).split(',') if s.strip()]) if sizes_value else 1
            color_count = len([c.strip() for c in str(colours_value).split(',') if c.strip()]) if colours_value else 1
            total_variants += size_count * color_count
            
            if str(published_value).lower() == 'active':
                active_products += 1
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<div class="stats-box"><h3>{len(df_raw)}</h3><p>Total Products</p></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="stats-box"><h3>{len(df_raw.columns)}</h3><p>Columns</p></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="stats-box"><h3>{total_variants}</h3><p>Est. Variants</p></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="stats-box"><h3>{active_products}</h3><p>Active Products</p></div>', unsafe_allow_html=True)
        
        # Check for pricing issues
        self._check_pricing_issues(df_raw, column_mapping)
    
    def _check_pricing_issues(self, df_raw, column_mapping):
        """Check for missing or zero prices"""
        price_column_actual = column_mapping.get('variant price')
        if not price_column_actual:
            for col in df_raw.columns:
                if 'price' in col.lower():
                    price_column_actual = col
                    break
        
        if price_column_actual and price_column_actual in df_raw.columns:
            zero_or_blank_prices = df_raw[
                (df_raw[price_column_actual] == 0) | 
                (df_raw[price_column_actual].isna()) | 
                (df_raw[price_column_actual] == "") |
                (pd.to_numeric(df_raw[price_column_actual], errors='coerce').fillna(0) == 0)
            ]
            
            if len(zero_or_blank_prices) > 0:
                total_products_with_zero_prices = len(zero_or_blank_prices)
                st.warning(f"⚠️ **PRICE ALERT**: {total_products_with_zero_prices} out of {len(df_raw)} products have missing or zero prices in the '{price_column_actual}' column.")
    
    def show_data_preview(self, df_raw, column_mapping):
        """Show data preview with column mapping"""
        # Show column mapping
        if column_mapping:
            with st.expander("🔍 Detected Column Mappings", expanded=False):
                st.write("The following columns were automatically detected (case-insensitive):")
                for standard_name, actual_column in column_mapping.items():
                    st.write(f"**{standard_name}** → `{actual_column}`")
        
        # Data preview tabs
        tab1, tab2 = st.tabs(["📊 Data Preview", "🔍 Column Analysis"])
        
        with tab1:
            st.dataframe(df_raw.head(10), use_container_width=True)
        
        with tab2:
            col_analysis = pd.DataFrame({
                'Column': df_raw.columns,
                'Data Type': df_raw.dtypes,
                'Non-Null Count': df_raw.count(),
                'Null Count': df_raw.isnull().sum(),
                'Sample Value': [str(df_raw[col].iloc[0]) if len(df_raw) > 0 else 'N/A' for col in df_raw.columns]
            })
            st.dataframe(col_analysis, use_container_width=True)
    
    def render_inventory_management(self, config):
        """Render inventory management interface with real-time feedback"""
        # Show current bulk mode status
        if config.get('bulk_qty_mode'):
            st.info(f"📦 Bulk mode enabled: Setting {config['bulk_qty']} for all variants")
        
        if config.get('bulk_compare_price_mode'):
            st.info(f"💰 Bulk compare price mode enabled: Setting ₹{config['bulk_compare_price']:.2f} for all variants")
        
        # Manual editing interface (only show if not in full bulk mode)
        if not (config.get('bulk_qty_mode') and config.get('bulk_compare_price_mode')):
            self._render_manual_inventory_management()
    
    def _render_manual_inventory_management(self):
        """Render manual inventory management interface"""
        if 'products_variants_grouped' not in st.session_state:
            products_variants = {}
            for size, color, title in st.session_state.unique_variants:
                if title not in products_variants:
                    products_variants[title] = []
                products_variants[title].append((size, color))
            st.session_state.products_variants_grouped = products_variants
        else:
            products_variants = st.session_state.products_variants_grouped
        
        st.markdown("### 🔧 Individual Variant Management")
        
        for product_title, variants in products_variants.items():
            total_qty = sum(st.session_state.variant_quantities.get(f"{size}|{color}|{product_title}", 0) 
                           for size, color in variants)
            total_variants = len(variants)
            
            with st.expander(f"📦 {product_title} ({total_variants} variants, {total_qty} total qty)", expanded=len(products_variants) <= 3):
                self._render_product_variant_form(product_title, variants)
        
        # Spreadsheet-style editing
        with st.expander("⚡ Power User: Spreadsheet-Style Editing", expanded=False):
            self._render_spreadsheet_editor()
    
    def _render_product_variant_form(self, product_title, variants):
        """Render form for individual product variant management"""
        with st.form(key=f"form_{hash(product_title) % 10000}"):
            variant_inputs = {}
            
            for size, color in variants:
                variant_key = f"{size}|{color}|{product_title}"
                current_qty = st.session_state.variant_quantities.get(variant_key, 0)
                current_compare_price = st.session_state.variant_compare_prices.get(variant_key, 0)
                
                extracted_qty = st.session_state.extracted_quantities.get((size, color, product_title), 0)
                extracted_compare_price = st.session_state.extracted_compare_prices.get((size, color, product_title), 0)
                
                col1, col2, col3 = st.columns([2, 2, 2])
                
                with col1:
                    st.markdown(f"**{size} / {color if color else 'N/A'}**")
                    if extracted_qty > 0:
                        st.caption(f"↗️ Extracted Qty: {extracted_qty}")
                    if extracted_compare_price > 0:
                        st.caption(f"💰 Extracted Compare: ₹{extracted_compare_price:.2f}")
                
                with col2:
                    qty = st.number_input(
                        "Quantity",
                        min_value=0,
                        value=int(current_qty),
                        step=1,
                        key=f"form_qty_{variant_key}_{hash(variant_key) % 10000}",
                        help=f"Extracted from size data: {extracted_qty}" if extracted_qty > 0 else "Manual quantity"
                    )
                
                with col3:
                    compare_price = st.number_input(
                        "Compare Price (₹)",
                        min_value=0.0,
                        value=float(current_compare_price),
                        step=1.0,
                        format="%.2f",
                        key=f"form_price_{variant_key}_{hash(variant_key) % 10000}",
                        help=f"Extracted from uploaded data: ₹{extracted_compare_price:.2f}" if extracted_compare_price > 0 else "Manual compare price"
                    )
                
                variant_inputs[variant_key] = (qty, compare_price)
            
            if st.form_submit_button(f"💾 Update {product_title}", use_container_width=True):
                for variant_key, (qty, compare_price) in variant_inputs.items():
                    st.session_state.variant_quantities[variant_key] = qty
                    st.session_state.variant_compare_prices[variant_key] = compare_price
                st.success(f"✅ Updated quantities and prices for {product_title}")
                # Force refresh to show changes in preview
                st.rerun()
    
    def _render_spreadsheet_editor(self):
        """Render spreadsheet-style editor for bulk variant editing"""
        st.markdown("*Excel-like interface for bulk editing*")
        
        # Create dataframe for editing
        variant_data = []
        for size, color, title in st.session_state.unique_variants:
            variant_key = f"{size}|{color}|{title}"
            extracted_qty = st.session_state.extracted_quantities.get((size, color, title), 0)
            extracted_compare_price = st.session_state.extracted_compare_prices.get((size, color, title), 0)
            
            current_qty = st.session_state.variant_quantities.get(variant_key, 0)
            current_compare_price = st.session_state.variant_compare_prices.get(variant_key, 0)
            
            variant_data.append({
                'Product': title,
                'Size': size if size else 'N/A',
                'Color': color if color else 'N/A',
                'Extracted Qty': extracted_qty,
                'Current Qty': current_qty,
                'Extracted Compare Price': extracted_compare_price,
                'Current Compare Price': current_compare_price,
                'Key': variant_key
            })
        
        variant_df = pd.DataFrame(variant_data)
        
        edited_variants = st.data_editor(
            variant_df[['Product', 'Size', 'Color', 'Extracted Qty', 'Current Qty', 'Extracted Compare Price', 'Current Compare Price']], 
            hide_index=True,
            use_container_width=True,
            key="variant_editor",
            column_config={
                'Extracted Qty': st.column_config.NumberColumn('Extracted Qty', disabled=True),
                'Current Qty': st.column_config.NumberColumn('Current Qty', min_value=0, step=1),
                'Extracted Compare Price': st.column_config.NumberColumn('Extracted Compare Price (₹)', disabled=True, format="%.2f"),
                'Current Compare Price': st.column_config.NumberColumn('Current Compare Price (₹)', min_value=0.0, step=0.01, format="%.2f")
            }
        )
        
        if st.button("💾 Apply All Spreadsheet Changes", key="apply_table", type="primary"):
            for i, variant_key in enumerate(variant_df['Key']):
                st.session_state.variant_quantities[variant_key] = int(edited_variants.iloc[i]['Current Qty'])
                st.session_state.variant_compare_prices[variant_key] = float(edited_variants.iloc[i]['Current Compare Price'])
    
    def show_final_statistics(self, shopify_csv):
        """Show final statistics before download with real-time updates"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f'<div class="stats-box"><h3>{len(shopify_csv)}</h3><p>Final Variants</p></div>', unsafe_allow_html=True)
        with col2:
            total_inventory = int(shopify_csv["Variant Inventory Qty"].sum()) if len(shopify_csv) > 0 else 0
            st.markdown(f'<div class="stats-box"><h3>{total_inventory}</h3><p>Total Inventory</p></div>', unsafe_allow_html=True)
        with col3:
            unique_products = shopify_csv["Handle"].nunique() if len(shopify_csv) > 0 else 0
            st.markdown(f'<div class="stats-box"><h3>{unique_products}</h3><p>Unique Products</p></div>', unsafe_allow_html=True)
        with col4:
            avg_price = shopify_csv["Variant Price"].replace(0, pd.NA).mean()
            avg_price_text = f"₹{avg_price:.0f}" if pd.notna(avg_price) else "N/A"
            st.markdown(f'<div class="stats-box"><h3>{avg_price_text}</h3><p>Avg Price</p></div>', unsafe_allow_html=True)
    
    def show_tabbed_results(self, shopify_csv):
        """Show results in tabbed interface with real-time data"""
        # Add a refresh indicator if config has changed recently
        if st.session_state.get('sidebar_config') and 'processed_data' in st.session_state:
            current_time = time.time()
            if not hasattr(st.session_state, 'last_config_change'):
                st.session_state.last_config_change = current_time
            
            if current_time - st.session_state.last_config_change < 3:  # Within 3 seconds
                st.info("🔄 Data refreshed based on your configuration changes")
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Final Preview", "📈 Inventory Summary", "🏷️ AI Tags Overview", "💰 Price Summary", "🧵 Product Details"])
        
        with tab1:
            # Show timestamp of data generation for real-time verification
            st.caption(f"Generated at: {time.strftime('%H:%M:%S')}")
            st.dataframe(shopify_csv.head(20), use_container_width=True)
        
        with tab2:
            self._show_inventory_summary(shopify_csv)
        
        with tab3:
            self._show_tags_summary(shopify_csv)
        
        with tab4:
            self._show_price_summary(shopify_csv)
        
        with tab5:
            self._show_product_details(shopify_csv)
    
    def _show_inventory_summary(self, shopify_csv):
        """Show inventory summary tab with real-time data"""
        try:
            inventory_summary = shopify_csv.groupby(["Handle", "Title"]).agg({
                "Variant Inventory Qty": ["sum", "count"],
                "Variant Price": "first",
                "Variant Compare At Price": "first"
            }).round(2)
            inventory_summary.columns = ["Total Qty", "Variants", "Price", "Compare Price"]
            
            # Add bulk mode indicators
            config = st.session_state.get('config', {})
            if config.get('bulk_qty_mode'):
                st.info(f"📦 Bulk Quantity Mode: All variants set to {config['bulk_qty']}")
            if config.get('bulk_compare_price_mode'):
                st.info(f"💰 Bulk Compare Price Mode: All variants set to ₹{config['bulk_compare_price']:.2f}")
            
            st.dataframe(inventory_summary, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating inventory summary: {e}")
            st.dataframe(shopify_csv[["Handle", "Title", "Variant Inventory Qty", "Variant Price", "Variant Compare At Price"]], use_container_width=True)
    
    def _show_tags_summary(self, shopify_csv):
        """Show AI tags summary tab"""
        config = st.session_state.get('config', {})
        if config.get('mode') != "Default template (no AI)":
            tags_df = shopify_csv[shopify_csv["Tags"] != ""][["Title", "Tags"]].drop_duplicates()
            if len(tags_df) > 0:
                st.dataframe(tags_df, use_container_width=True)
            else:
                st.info("No AI tags generated")
        else:
            st.info("No AI tags generated in current mode")
    
    def _show_price_summary(self, shopify_csv):
        """Show price summary tab with real-time config indicators"""
        config = st.session_state.get('config', {})
        
        # Show active pricing configurations
        if config.get('enable_surcharge') and config.get('surcharge_rules'):
            st.info(f"📈 Size Surcharges Active: {list(config['surcharge_rules'].keys())}")
        
        try:
            price_summary = shopify_csv[shopify_csv["Variant Price"] > 0].groupby(["Handle", "Title"]).agg({
                "Variant Price": ["min", "max", "mean"],
                "Variant Compare At Price": ["min", "max", "mean"]
            }).round(2)
            price_summary.columns = ["Min Price", "Max Price", "Avg Price", "Min Compare", "Max Compare", "Avg Compare"]
            st.dataframe(price_summary, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating price summary: {e}")
            st.dataframe(shopify_csv[["Handle", "Title", "Variant Price", "Variant Compare At Price"]], use_container_width=True)
    
    def _show_product_details(self, shopify_csv):
        """Show product details tab"""
        try:
            # Show configuration-dependent details
            config = st.session_state.get('config', {})
            
            st.markdown("### Current Configuration Impact")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Vendor Name", config.get('vendor_name', 'N/A'))
                st.metric("Inventory Policy", config.get('inventory_policy', 'N/A'))
                st.metric("AI Mode", config.get('mode', 'N/A'))
            
            with col2:
                bulk_qty = "Yes" if config.get('bulk_qty_mode') else "No"
                bulk_price = "Yes" if config.get('bulk_compare_price_mode') else "No"
                surcharge = "Yes" if config.get('enable_surcharge') else "No"
                
                st.metric("Bulk Quantity Mode", bulk_qty)
                st.metric("Bulk Compare Price Mode", bulk_price)
                st.metric("Size Surcharges", surcharge)
            
            # Sample product details
            if len(shopify_csv) > 0:
                st.markdown("### Sample Product Details")
                sample_product = shopify_csv[shopify_csv["Title"] != ""].iloc[0]
                st.json({
                    "Handle": sample_product.get("Handle", ""),
                    "Title": sample_product.get("Title", ""),
                    "Vendor": sample_product.get("Vendor", ""),
                    "Type": sample_product.get("Type", ""),
                    "Tags": sample_product.get("Tags", "")
                })
        except Exception as e:
            st.error(f"Error creating details summary: {e}")
    
    def render_download_section(self, shopify_csv):
        """Render download section with success message and real-time data info"""
        csv_data = shopify_csv.to_csv(index=False).encode("utf-8")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="📥 Download Shopify CSV",
                data=csv_data,
                file_name=f"shopify_import_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True
            )
        
        with col2:
            if st.button("🔄 Process Another File", use_container_width=True):
                # Clear all session state for fresh start
                keys_to_clear = [
                    'processed_data', 'column_mapping', 'config', 'unique_variants',
                    'variant_products', 'extracted_quantities', 'extracted_compare_prices',
                    'variant_quantities', 'variant_compare_prices', 'unique_variants_processed',
                    'products_variants_grouped', 'sidebar_config'
                ]
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        
        # Show current config summary for verification
        config = st.session_state.get('config', {})
        config_summary = []
        if config.get('bulk_qty_mode'):
            config_summary.append(f"Bulk Qty: {config['bulk_qty']}")
        if config.get('bulk_compare_price_mode'):
            config_summary.append(f"Bulk Compare: ₹{config['bulk_compare_price']:.2f}")
        if config.get('enable_surcharge'):
            config_summary.append(f"Surcharges: {len(config.get('surcharge_rules', {}))}")
        
        if config_summary:
            st.info(f"✅ Applied Settings: {' | '.join(config_summary)}")
        
        st.success("🎉 Your Shopify CSV is ready! The file contains all variants with real-time configuration applied.")
        
        with st.expander("💡 Next Steps & Tips"):
            st.markdown("""
            ### 📋 What to do next:
            1. **Download** your CSV file using the button above
            2. **Review** the data in Excel/Google Sheets if needed
            3. **Import** to Shopify via: Products → Import
            4. **Check** that all variants imported correctly
            
            ### ⚠️ Important Notes:
            - Configuration changes are applied in real-time to the preview and download
            - Make sure your Shopify store accepts the product categories used
            - Verify that all image URLs (if any) are accessible
            - Double-check pricing and inventory levels
            - Test with a small batch first if you have many products
            - Sizes are automatically sorted: XS, S, M, L, XL, XXL, XXXL, then custom sizes
            
            ### 🔄 Real-time Features:
            - All sidebar configuration changes update the preview immediately
            - Bulk quantity and pricing modes override individual settings
            - Size surcharges are calculated and applied automatically
            - Vendor name and inventory policy changes reflect instantly
            """)