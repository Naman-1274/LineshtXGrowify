# frontend/ui_components.py - FIXED: No decimals in preview
import streamlit as st
import pandas as pd
import time
from helpers.utils import get_column_value, clean_value

class UIComponents:    
    def apply_styling(self):
        """Apply enhanced CSS styling with step indicators"""
        st.markdown("""
        <style>
            .main-header {
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                padding: 2rem; border-radius: 10px; color: white; text-align: center;
                margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .step-progress {
                background: linear-gradient(45deg, #f093fb 0%, #f5576c 100%);
                padding: 1rem; border-radius: 8px; color: white; margin: 1rem 0;
                display: flex; justify-content: space-between; align-items: center;
            }
            .step-item {
                flex: 1; text-align: center; padding: 0.5rem;
            }
            .step-active {
                background: rgba(255,255,255,0.3); border-radius: 5px; font-weight: bold;
            }
            .step-complete {
                color: #90EE90;
            }
            .step-header {
                background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
                padding: 1rem; border-radius: 8px; color: white; margin: 1rem 0;
            }
            .stats-box {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; padding: 1rem; border-radius: 8px; text-align: center; margin: 0.5rem;
            }
            .column-mapping-card {
                background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px;
                padding: 1rem; margin: 0.5rem 0;
            }
            .confidence-high { color: #28a745; font-weight: bold; }
            .confidence-medium { color: #ffc107; font-weight: bold; }
            .confidence-low { color: #dc3545; font-weight: bold; }
            .preview-box {
                background: linear-gradient(45deg, #232526 0%, #414345 100%);
                padding: 1rem; border-radius: 8px; color: white; margin: 1rem 0;
            }
            .metafield-section {
                background: #e3f2fd; border-left: 4px solid #2196F3; 
                padding: 1rem; margin: 1rem 0; border-radius: 4px;
            }
            .info-badge {
                background: #2196F3; color: white; padding: 0.25rem 0.5rem;
                border-radius: 12px; font-size: 0.75rem; margin-left: 0.5rem;
            }
        </style>
        """, unsafe_allow_html=True)
    
    def render_header_with_progress(self):
        """Render application header with step progress indicator"""
        st.markdown("""
        <div class="main-header">
            <h1>🛍️ Advanced Shopify CSV Builder</h1>
            <p>Transform your product data into Shopify-ready imports with AI-powered descriptions</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Step progress indicator
        current_step = st.session_state.get('step', 1)
        steps = [
            "Upload", "Map Columns", "Build Descriptions", 
            "AI Processing", "Inventory", "Generate CSV"
        ]
        
        progress_html = '<div class="step-progress">'
        for i, step_name in enumerate(steps, 1):
            if i == current_step:
                progress_html += f'<div class="step-item step-active">🔹 {i}. {step_name}</div>'
            elif i < current_step:
                progress_html += f'<div class="step-item step-complete">✅ {i}. {step_name}</div>'
            else:
                progress_html += f'<div class="step-item">⚫ {i}. {step_name}</div>'
        progress_html += '</div>'
        
        st.markdown(progress_html, unsafe_allow_html=True)
        st.markdown("---")
    
    def show_ai_status(self, ai_enabled):
        """Display AI service status"""
        status = "✅ AI Features Enabled" if ai_enabled else "⚠️ AI Features Disabled"
        st.info(status)
    
    def render_step_header(self, title):
        """Render section header"""
        st.markdown(f'<div class="step-header"><h2>{title}</h2></div>', unsafe_allow_html=True)
    
    def render_sidebar_config(self, ai_enabled):
        """Render sidebar configuration for final step"""
        with st.sidebar:
            st.markdown("## ⚙️ Configuration")
            
            config = st.session_state.get('config', {})
            
            # AI Processing mode
            config['mode'] = st.radio(
                "🤖 AI Processing Mode:",
                options=[
                    "Default template (no AI)",
                    "Simple mode (first sentence + tags)",
                    "Full AI mode (custom description + tags)"
                ],
                index=["Default template (no AI)", "Simple mode (first sentence + tags)", 
                      "Full AI mode (custom description + tags)"].index(config.get('mode', "Default template (no AI)")),
                disabled=not ai_enabled
            )
            
            st.markdown("---")
            
            # Brand settings
            config['vendor_name'] = st.text_input("Vendor Name", value=config.get('vendor_name', 'YourBrandName'))
            
            # Inventory settings
            config['inventory_policy'] = st.selectbox(
                "Inventory Policy", 
                ["deny", "continue"],
                index=0 if config.get('inventory_policy', 'deny') == 'deny' else 1
            )
            config['default_qty'] = st.number_input(
                "Default Quantity", 
                min_value=0, 
                value=config.get('default_qty', 10), 
                step=1
            )
            
            config['bulk_qty_mode'] = st.checkbox("Bulk Quantity Override", value=config.get('bulk_qty_mode', False))
            if config['bulk_qty_mode']:
                config['bulk_qty'] = st.number_input("Bulk Quantity", min_value=0, value=config.get('bulk_qty', config['default_qty']), step=1)
            
            # Price settings
            config['default_compare_price'] = st.number_input("Default Compare Price", min_value=0.0, value=config.get('default_compare_price', 0.0), step=0.01)
            config['bulk_compare_price_mode'] = st.checkbox("Bulk Compare Price", value=config.get('bulk_compare_price_mode', False))
            if config['bulk_compare_price_mode']:
                config['bulk_compare_price'] = st.number_input("Bulk Compare Price", min_value=0.0, value=config.get('bulk_compare_price', 0.0), step=0.01)
            
            # Size surcharge
            config['enable_surcharge'] = st.checkbox("Enable Size Surcharge", value=config.get('enable_surcharge', False))
            config['surcharge_rules'] = config.get('surcharge_rules', {})
            if config['enable_surcharge']:
                num_rules = st.number_input("Number of surcharge rules", min_value=1, value=max(1, len(config['surcharge_rules'])), step=1)
                new_rules = {}
                for i in range(int(num_rules)):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        existing_sizes = list(config['surcharge_rules'].keys())
                        default_size = existing_sizes[i] if i < len(existing_sizes) else ""
                        size = st.text_input(f"Size {i+1}", value=default_size, key=f"size_{i}").upper().strip()
                    with col2:
                        default_percent = config['surcharge_rules'].get(existing_sizes[i], 0) * 100 if i < len(existing_sizes) else 0
                        percent = st.number_input(f"%", min_value=0.0, value=float(default_percent), step=0.5, key=f"percent_{i}")
                    if size and percent > 0:
                        new_rules[size] = percent / 100.0
                config['surcharge_rules'] = new_rules
            
            # Reset controls
            st.markdown("---")
            if st.button("🆕 Process New File"):
                st.session_state.clear()
                st.rerun()
            
            return config
    
    def render_file_upload(self):
        """Enhanced file upload section with metrics"""
        st.header("📁 Step 1: Upload Your Product Data")
        
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            uploaded_file = st.file_uploader(
                "Choose your CSV or Excel file",
                type=["csv", "xlsx"],
                help="Upload a file containing your product data"
            )
        
        if uploaded_file:
            with col2:
                file_size = len(uploaded_file.getvalue()) / 1024
                st.metric("File Size", f"{file_size:.1f} KB")
            with col3:
                file_type = "Excel" if uploaded_file.name.lower().endswith(".xlsx") else "CSV"
                st.metric("File Type", file_type)
        
        return uploaded_file
    
    def show_file_metrics(self, df):
        """Display enhanced file loading metrics"""
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<div class="stats-box"><h3>{len(df)}</h3><p>Products</p></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="stats-box"><h3>{len(df.columns)}</h3><p>Columns</p></div>', unsafe_allow_html=True)
        with col3:
            est_variants = len(df) * 2  # Rough estimate
            st.markdown(f'<div class="stats-box"><h3>{est_variants}</h3><p>Est. Variants</p></div>', unsafe_allow_html=True)
        with col4:
            non_null = df.count().sum()
            st.markdown(f'<div class="stats-box"><h3>{non_null}</h3><p>Data Points</p></div>', unsafe_allow_html=True)
        
        # Enhanced preview
        st.subheader("Data Preview")
        st.dataframe(df.head(), use_container_width=True)
    
    def render_enhanced_column_mapping(self, df, mapping_result):
        """Enhanced column mapping with complete Shopify fields including metafields"""
        st.header("📊 Step 2: Review & Edit Column Mapping")
        
        # Show mapping summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("✅ Auto-Mapped", len(mapping_result.base_mapping))
        with col2:
            st.metric("❓ Unmapped", len(mapping_result.unmapped_columns))
        with col3:
            st.metric("📊 Total Columns", len(df.columns))
        
        # Complete Shopify CSV fields
        st.subheader("Map Your Columns to Shopify Fields")
        st.info("🔍 Map your data columns to Shopify CSV fields. NEW: Now includes metafields for enhanced product data!")
        
        # Initialize mapping state if not exists
        if 'current_column_mapping' not in st.session_state:
            st.session_state.current_column_mapping = mapping_result.base_mapping.copy()
        
        # Create tabs for better organization
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🔑 Essential Fields", 
            "📋 Product Details", 
            "🖼️ Images & SEO", 
            "🛒 Google Shopping",
            "🏷️ Metafields (NEW)"
        ])
        
        # Essential fields
        essential_fields = [
            'Handle', 'Title', 'Body (HTML)', 'Vendor', 'Product Category', 'Type', 'Tags', 'Published',
            'Option1 Value', 'Option2 Value', 'Variant SKU', 'Variant Price', 'Variant Compare At Price',
            'Variant Inventory Qty', 'Variant Inventory Policy'
        ]
        
        with tab1:
            st.markdown("**Most commonly used fields for Shopify import:**")
            self._render_mapping_section(df, essential_fields, mapping_result.confidence_scores)
        
        # Product details
        product_fields = [
            'Option1 Name', 'Option1 Linked To', 'Option2 Name', 'Option2 Linked To', 
            'Option3 Name', 'Option3 Value', 'Option3 Linked To',
            'Variant Grams', 'Variant Inventory Tracker', 'Variant Fulfillment Service',
            'Variant Requires Shipping', 'Variant Taxable', 'Variant Barcode', 
            'Variant Image', 'Variant Weight Unit', 'Variant Weight', 'Gift Card', 'Status',
            'Unit Price Total Measure', 'Unit Price Total Measure Unit',
            'Unit Price Base Measure', 'Unit Price Base Measure Unit'
        ]
        
        with tab2:
            st.markdown("**Additional product and variant details:**")
            st.info("💡 NEW: Unit Price fields for pricing per measure (e.g., per kg, per liter)")
            self._render_mapping_section(df, product_fields, mapping_result.confidence_scores)
        
        # Images and SEO
        image_seo_fields = [
            'Image Src', 'Image Position', 'Image Alt Text', 
            'SEO Title', 'SEO Description', 'Cost per item',
            'Price / International', 'Compare At Price / International'
        ]
        
        with tab3:
            st.markdown("**Images, SEO, and pricing fields:**")
            self._render_mapping_section(df, image_seo_fields, mapping_result.confidence_scores)
        
        # Google Shopping
        google_fields = [
            'Google Shopping / Google Product Category', 'Google Shopping / Gender',
            'Google Shopping / Age Group', 'Google Shopping / MPN',
            'Google Shopping / AdWords Grouping', 'Google Shopping / AdWords Labels',
            'Google Shopping / Condition', 'Google Shopping / Custom Product',
            'Google Shopping / Custom Label 0', 'Google Shopping / Custom Label 1',
            'Google Shopping / Custom Label 2', 'Google Shopping / Custom Label 3',
            'Google Shopping / Custom Label 4'
        ]
        
        with tab4:
            st.markdown("**Google Shopping and advertising fields:**")
            self._render_mapping_section(df, google_fields, mapping_result.confidence_scores)
        
        # NEW: Metafields tab
        metafield_fields = [
            'Gender (product.metafields.custom.gender)',
            'Google: Custom Product (product.metafields.mm-google-shopping.custom_product)',
            'Age group (product.metafields.shopify.age-group)',
            'Color (product.metafields.shopify.color-pattern)',
            'Dress occasion (product.metafields.shopify.dress-occasion)',
            'Dress style (product.metafields.shopify.dress-style)',
            'Fabric (product.metafields.shopify.fabric)',
            'Neckline (product.metafields.shopify.neckline)',
            'Size (product.metafields.shopify.size)',
            'Skirt/Dress length type (product.metafields.shopify.skirt-dress-length-type)',
            'Sleeve length type (product.metafields.shopify.sleeve-length-type)',
            'Target gender (product.metafields.shopify.target-gender)',
            'Complementary products (product.metafields.shopify--discovery--product_recommendation.complementary_products)',
            'Related products (product.metafields.shopify--discovery--product_recommendation.related_products)',
            'Related products settings (product.metafields.shopify--discovery--product_recommendation.related_products_display)',
            'Search product boosts (product.metafields.shopify--discovery--product_search_boost.queries)'
        ]
        
        with tab5:
            st.markdown('<div class="metafield-section">', unsafe_allow_html=True)
            st.markdown("### 🏷️ **Product Metafields** <span class='info-badge'>NEW IN SHOPIFY</span>", unsafe_allow_html=True)
            st.markdown("""
            **What are Metafields?**  
            Metafields are custom data fields that enhance your product information. They enable:
            - Better product filtering and search
            - Enhanced product recommendations
            - Richer product details for customers
            - Improved SEO and discoverability
            
            **Auto-Populated Metafields:**
            - 🎨 **Color** - Auto-filled from your color column
            - 🧵 **Fabric** - Auto-filled from your fabric column
            - 📏 **Size** - Auto-filled from your size option
            """)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Product attribute metafields
            st.markdown("#### 👕 Product Attributes")
            product_metafields = [
                'Gender (product.metafields.custom.gender)',
                'Age group (product.metafields.shopify.age-group)',
                'Color (product.metafields.shopify.color-pattern)',
                'Fabric (product.metafields.shopify.fabric)',
                'Size (product.metafields.shopify.size)',
                'Target gender (product.metafields.shopify.target-gender)'
            ]
            self._render_mapping_section(df, product_metafields, mapping_result.confidence_scores, show_auto_populate=True)
            
            # Fashion-specific metafields
            st.markdown("#### 👗 Fashion & Apparel")
            fashion_metafields = [
                'Dress occasion (product.metafields.shopify.dress-occasion)',
                'Dress style (product.metafields.shopify.dress-style)',
                'Neckline (product.metafields.shopify.neckline)',
                'Skirt/Dress length type (product.metafields.shopify.skirt-dress-length-type)',
                'Sleeve length type (product.metafields.shopify.sleeve-length-type)'
            ]
            self._render_mapping_section(df, fashion_metafields, mapping_result.confidence_scores)
            
            # Discovery & recommendations
            st.markdown("#### 🔍 Product Discovery & Recommendations")
            discovery_metafields = [
                'Complementary products (product.metafields.shopify--discovery--product_recommendation.complementary_products)',
                'Related products (product.metafields.shopify--discovery--product_recommendation.related_products)',
                'Related products settings (product.metafields.shopify--discovery--product_recommendation.related_products_display)',
                'Search product boosts (product.metafields.shopify--discovery--product_search_boost.queries)'
            ]
            with st.expander("ℹ️ Advanced Discovery Settings", expanded=False):
                st.markdown("""
                **Product Recommendations:**
                - Complementary products: Suggest items that go well together
                - Related products: Show similar items
                
                **Search Optimization:**
                - Search boosts: Prioritize products for specific search terms
                """)
                self._render_mapping_section(df, discovery_metafields, mapping_result.confidence_scores)
            
            # Google Shopping metafield
            st.markdown("#### 🛒 Google Shopping")
            google_metafields = [
                'Google: Custom Product (product.metafields.mm-google-shopping.custom_product)'
            ]
            self._render_mapping_section(df, google_metafields, mapping_result.confidence_scores)
        
        # Show column reuse info
        used_columns = [col for col in st.session_state.current_column_mapping.values() if col]
        reused_columns = [col for col in set(used_columns) if used_columns.count(col) > 1]
        if reused_columns:
            st.info(f"📋 Columns used multiple times: {', '.join(reused_columns)} (This is fine - columns can serve multiple purposes)")
        
        # Show mapping summary
        mapped_count = len([v for v in st.session_state.current_column_mapping.values() if v])
        metafield_count = len([k for k, v in st.session_state.current_column_mapping.items() if v and 'metafields' in k])
        
        # Add reset button
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🔄 Reset All Mappings", help="Clear all column mappings and start fresh"):
                st.session_state.current_column_mapping = {}
                st.rerun()
        with col2:
            if metafield_count > 0:
                st.success(f"✅ {mapped_count} fields mapped ({metafield_count} metafields) • All {len(df.columns)} columns available for descriptions")
            else:
                st.success(f"✅ {mapped_count} fields mapped • All {len(df.columns)} columns available for descriptions")
        
        return st.session_state.current_column_mapping.copy()
    
    def _render_mapping_section(self, df, fields, confidence_scores, show_auto_populate=False):
        """Render a section of mapping fields with optional auto-populate indicators"""
        auto_populate_fields = {
            'Color (product.metafields.shopify.color-pattern)': 'colour',
            'Fabric (product.metafields.shopify.fabric)': 'fabric',
            'Size (product.metafields.shopify.size)': 'size'
        }
        
        for field in fields:
            col1, col2, col3 = st.columns([2, 3, 1])
            
            with col1:
                # Show field name with indicators
                if field in ['Handle', 'Title', 'Variant SKU', 'Variant Price']:
                    st.markdown(f"**{field}** ⭐")
                elif show_auto_populate and field in auto_populate_fields:
                    st.markdown(f"**{field}** 🤖")
                    st.caption("Auto-populated")
                else:
                    st.text(field)
            
            with col2:
                # Get current mapping
                current = st.session_state.current_column_mapping.get(field, '')
                
                # Make ALL columns available for maximum flexibility
                available_columns = [""] + list(df.columns)
                
                # Create unique key for each selectbox
                selected = st.selectbox(
                    "Map to column:",
                    options=available_columns,
                    index=available_columns.index(current) if current in available_columns else 0,
                    key=f"mapping_{field}_{hash(field)}",
                    label_visibility="collapsed"
                )
                
                # Update mapping in session state
                if selected != current:
                    st.session_state.current_column_mapping[field] = selected
            
            with col3:
                # Show confidence score if available
                if current and current in confidence_scores:
                    confidence = confidence_scores[current]
                    st.caption(f"{confidence:.0%}")
                elif current:
                    st.caption("Manual")
                else:
                    st.caption("")
    
    def render_description_builder(self, df, column_mapping):
        """Dynamic description builder interface"""
        st.header("📝 Step 3: Build Product Descriptions")
        
        st.info("🎨 Create dynamic product descriptions by selecting columns and customizing their display format.")
        
        # Get available columns (ALL columns - including mapped ones for maximum flexibility)
        all_columns = list(df.columns)
        
        # Show which columns are used in main template for reference
        mapped_columns = set(column_mapping.values())
        if mapped_columns:
            with st.expander("ℹ️ Column Usage Reference", expanded=False):
                st.write("**Columns used in main Shopify template:**")
                for standard_field, actual_column in column_mapping.items():
                    if actual_column:
                        st.write(f"• {actual_column} → {standard_field}")
                st.write("**Note:** You can still use these columns in descriptions for additional context.")
        
        # Description elements management
        description_elements = st.session_state.get('description_elements', [])
        
        # Auto-initialize with main description if available and empty
        if not description_elements:
            main_desc = column_mapping.get('Body (HTML)', '')
            if main_desc and main_desc in df.columns:
                description_elements = [{
                    'column': main_desc,
                    'label': 'Product Description',
                    'html_tag': 'p',
                    'order': 1
                }]
                st.session_state.description_elements = description_elements
        
        # Add/Remove elements controls
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("➕ Add Element"):
                description_elements.append({
                    'column': '',
                    'label': '',
                    'html_tag': 'p',
                    'order': len(description_elements) + 1
                })
                st.session_state.description_elements = description_elements
                st.rerun()
        
        with col2:
            if description_elements and st.button("➖ Remove Last"):
                description_elements.pop()
                st.session_state.description_elements = description_elements
                st.rerun()
        
        with col3:
            st.caption(f"Current elements: {len(description_elements)}")
        
        # Configure elements
        html_tags = {
            'p': 'Paragraph',
            'h3': 'Heading 3',
            'h4': 'Heading 4',
            'strong': 'Bold',
            'li': 'List Item',
            'div': 'Division',
            'br': 'Line Break',
            'none': 'No HTML tags'
        }
        
        st.subheader("Configure Description Elements")
        
        for i, element in enumerate(description_elements):
            with st.container():
                st.markdown(f"**Element {i+1}**")
                
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                
                with col1:
                    element['column'] = st.selectbox(
                        "Column:",
                        options=[''] + all_columns,
                        index=all_columns.index(element['column']) + 1 if element['column'] in all_columns else 0,
                        key=f"col_{i}"
                    )
                
                with col2:
                    element['label'] = st.text_input(
                        "Label:",
                        value=element.get('label', ''),
                        placeholder="e.g., Fabric, Size, Color",
                        key=f"label_{i}"
                    )
                
                with col3:
                    element['html_tag'] = st.selectbox(
                        "HTML Tag:",
                        options=list(html_tags.keys()),
                        format_func=lambda x: html_tags[x],
                        index=list(html_tags.keys()).index(element.get('html_tag', 'p')),
                        key=f"tag_{i}"
                    )
                
                with col4:
                    element['order'] = st.number_input(
                        "Order:",
                        min_value=1,
                        value=element.get('order', i+1),
                        key=f"order_{i}"
                    )
                
                # Show sample data - FIXED: Use _clean_value_no_decimals
                if element['column'] and element['column'] in df.columns:
                    sample = df[element['column']].dropna().iloc[0] if not df[element['column']].dropna().empty else "No data"
                    # Clean sample to remove decimals
                    sample_clean = self._clean_value_no_decimals(sample, element['column'])
                    st.caption(f"Sample: {str(sample_clean)[:100]}...")
                
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Live Preview - FIXED: Use no-decimal version
        if description_elements:
            st.subheader("Live Preview")
            
            # Sort elements by order
            sorted_elements = sorted([elem for elem in description_elements if elem['column']], 
                                   key=lambda x: x.get('order', 0))
            
            # Generate preview
            if len(df) > 0 and sorted_elements:
                sample_row = df.iloc[0]
                preview_html = self._generate_description_html_no_decimals(sorted_elements, sample_row)
                
                st.markdown("**HTML Output:**")
                st.markdown(f'<div class="preview-box">{preview_html}</div>', unsafe_allow_html=True)
                
                with st.expander("📋 HTML Code"):
                    st.code(preview_html, language="html")
        
        return description_elements
    
    def _generate_description_html_no_decimals(self, elements, row):
        """FIXED: Generate HTML - tags ONLY on labels, values ALWAYS in <p>"""
        html_parts = []
        
        for element in elements:
            column = element.get('column', '')
            label = element.get('label', '')
            html_tag = element.get('html_tag', 'p')
            
            if column and column in row.index:
                # Use no-decimal cleaning
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
        
        return "".join(html_parts)
    
    def _clean_value_no_decimals(self, value, column_name: str = '') -> str:
        """FIXED: Remove decimals from ALL numeric values that should be integers"""
        if pd.isna(value) or str(value).strip() == '':
            return ""
        
        # Fields that should ALWAYS be integers (no decimals)
        integer_fields = [
            'no of components', 'components', 'number_of_components', 
            'component_count', 'quantity', 'qty', 'count', 'pieces',
            'set', 'items', 'number', 'no', 'component'
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
    
    def _clean_value(self, value):
        """Clean value for display (legacy support)"""
        if pd.isna(value) or str(value).strip() == '':
            return ""
        return str(value).strip()
    
    def render_column_mapping_review(self, df, mapping_result):
        """Render the column mapping review interface (legacy support)"""
        st.markdown("### 📊 Automatic Column Detection Results")
        
        # Show mapping summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("✅ Auto-Mapped", len(mapping_result.base_mapping))
        with col2:
            st.metric("❓ Unmapped", len(mapping_result.unmapped_columns))
        with col3:
            st.metric("📊 Total Columns", len(df.columns))
        
        # Show automatically mapped columns
        if mapping_result.base_mapping:
            st.markdown("#### ✅ Successfully Mapped Columns")
            mapped_data = []
            for standard_name, actual_column in mapping_result.base_mapping.items():
                confidence = mapping_result.confidence_scores.get(actual_column, 1.0)
                confidence_label = self._get_confidence_label(confidence)
                mapped_data.append({
                    "Standard Field": standard_name,
                    "Your Column": actual_column,
                    "Confidence": f"{confidence:.1%}",
                    "Status": confidence_label
                })
            
            st.dataframe(pd.DataFrame(mapped_data), hide_index=True, use_container_width=True)
        
        # Handle unmapped columns
        enhanced_mapping = {}
        column_descriptions = {}
        
        if mapping_result.unmapped_columns:
            st.markdown("#### ❓ Unmapped Columns")
            enhanced_mapping, column_descriptions = self._render_column_assignment_interface(
                df, mapping_result.unmapped_columns, mapping_result.base_mapping
            )
        
        return enhanced_mapping, column_descriptions
    
    def _render_column_assignment_interface(self, df, unmapped_columns, existing_mapping):
        """Render interface for assigning unmapped columns"""
        st.info("Choose how to handle each unmapped column:")
        
        # Initialize session state
        if 'column_assignments' not in st.session_state:
            st.session_state.column_assignments = {}
        if 'enhanced_column_mapping' not in st.session_state:
            st.session_state.enhanced_column_mapping = {}
        if 'column_descriptions' not in st.session_state:
            st.session_state.column_descriptions = {}
        if 'column_html_tags' not in st.session_state:
            st.session_state.column_html_tags = {}
        
        assignment_options = {
            'ignore': '🚫 Ignore',
            'description': '📝 Add to Description',
            'both': '🔄 Map to Field AND Description',
            'field_only': '🗂️ Map to Standard Field',
            'custom_field': '📋 Add as Custom Field'
        }
        
        taken_fields = set(existing_mapping.keys())
        
        for col in unmapped_columns:
            st.markdown(f"#### 📋 Column: `{col}`")
            
            # Show sample data
            sample_data = df[col].dropna().head(3).tolist()
            if sample_data:
                st.caption(f"Sample: {', '.join(str(x) for x in sample_data)}")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                assignment = st.selectbox(
                    "Action:",
                    options=list(assignment_options.keys()),
                    format_func=lambda x: assignment_options[x],
                    key=f"assign_{col}",
                    index=list(assignment_options.keys()).index(
                        st.session_state.column_assignments.get(col, 'ignore')
                    )
                )
                st.session_state.column_assignments[col] = assignment
            
            with col2:
                self._render_assignment_options(col, assignment, taken_fields, existing_mapping)
        
        return st.session_state.enhanced_column_mapping.copy(), st.session_state.column_descriptions.copy()
    
    def _render_assignment_options(self, col, assignment, taken_fields, existing_mapping):
        """Render options based on assignment type"""
        if assignment in ['both', 'field_only']:
            available_fields = self._get_available_standard_fields(taken_fields, existing_mapping)
            if available_fields:
                mapped_field = st.selectbox(
                    "Map to field:",
                    options=[''] + available_fields,
                    key=f"field_{col}"
                )
                if mapped_field:
                    st.session_state.enhanced_column_mapping[mapped_field] = col
                    taken_fields.add(mapped_field)
        
        elif assignment == 'custom_field':
            st.info(f"✅ '{col}' will be added as custom field")
            st.session_state.enhanced_column_mapping[col] = col
        
        if assignment in ['both', 'description']:
            self._render_description_options(col)
    
    def _render_description_options(self, col):
        """Render description options with HTML tags"""
        col1, col2 = st.columns([1, 1])
        
        with col1:
            desc_label = st.text_input(
                "Description label:",
                value=st.session_state.column_descriptions.get(col, col),
                key=f"desc_{col}"
            )
            st.session_state.column_descriptions[col] = desc_label
        
        with col2:
            html_tags = {
                'p': 'Paragraph <p>',
                'h3': 'Heading <h3>',
                'h4': 'Heading <h4>',
                'strong': 'Bold <strong>',
                'em': 'Italic <em>',
                'li': 'List item <li>',
                'div': 'Division <div>',
                'br': 'Line break <br>',
                'none': 'No HTML tags'
            }
            
            selected_tag = st.selectbox(
                "HTML tag:",
                options=list(html_tags.keys()),
                format_func=lambda x: html_tags[x],
                key=f"html_{col}",
                index=list(html_tags.keys()).index(
                    st.session_state.column_html_tags.get(col, 'p')
                )
            )
            st.session_state.column_html_tags[col] = selected_tag
        
        # Preview
        if desc_label:
            preview = self._generate_html_preview(desc_label, "Sample content", selected_tag)
            st.markdown("**Preview:**")
            st.markdown(f'<div style="background:#f8f9fa;padding:0.5rem;border-radius:4px;">{preview}</div>', unsafe_allow_html=True)
    
    def _generate_html_preview(self, label, content, tag):
        """Generate HTML preview"""
        full_content = f"{label}: {content}" if label != content else content
        if tag == 'none':
            return full_content
        elif tag == 'br':
            return f"{full_content}<br>"
        else:
            return f"<{tag}>{full_content}</{tag}>"
    
    def _get_confidence_label(self, confidence):
        """Get confidence label with styling"""
        if confidence >= 0.9:
            return "🟢 High"
        elif confidence >= 0.7:
            return "🟡 Medium"
        else:
            return "🔴 Low"
    
    def _get_available_standard_fields(self, taken_fields, existing_mapping):
        """Get available standard fields for mapping"""
        all_fields = [
            "Handle", "Title", "Vendor", "Product Category", "Type", "Tags",
            "Variant SKU", "Variant Price", "Variant Compare At Price"
        ]
        return [field for field in all_fields if field not in taken_fields and field not in existing_mapping]
    
    def show_data_preview(self, df, column_mapping):
        """Show data preview"""
        tab1, tab2 = st.tabs(["📊 Data Preview", "📋 Column Analysis"])
        
        with tab1:
            st.dataframe(df.head(10), use_container_width=True)
        
        with tab2:
            col_analysis = pd.DataFrame({
                'Column': df.columns,
                'Type': df.dtypes,
                'Non-Null': df.count(),
                'Sample': [str(df[col].iloc[0]) if len(df) > 0 else 'N/A' for col in df.columns]
            })
            st.dataframe(col_analysis, use_container_width=True)
    
    def render_inventory_management(self, config):
        pass
    
    def render_variant_editor(self, variants_data):
        """Render variant quantity/price editor with extracted quantities displayed"""
        if not variants_data.get('unique_variants'):
            return
        
        st.markdown("### Variant Management")
        
        # Group variants by product
        products = {}
        for variant_key in variants_data['unique_variants']:
            size, color, title = variant_key
            if title not in products:
                products[title] = []
            products[title].append((size, color))
        
        # Show first few products expanded
        for idx, (title, variants) in enumerate(products.items()):
            expanded = idx < 3
            with st.expander(f"{title} ({len(variants)} variants)", expanded=expanded):
                for size, color in variants:
                    variant_key = f"{size}|{color}|{title}"
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    
                    with col1:
                        display = f"{size}" if size else "No Size"
                        if color:
                            display += f" - {color}"
                        st.text(display)
                    
                    with col2:
                        # Get extracted quantity from data (if available)
                        extracted_qty = variants_data.get('extracted_quantities', {}).get(variant_key, 0)
                        if extracted_qty > 0:
                            st.caption(f"Data: {extracted_qty}")
                        else:
                            st.caption("No data qty")
                    
                    with col3:
                        current_qty = st.session_state.variant_quantities.get(variant_key, extracted_qty)
                        new_qty = st.number_input(
                            "Qty", min_value=0, value=int(current_qty), step=1,
                            key=f"qty_{variant_key}", label_visibility="collapsed"
                        )
                        st.session_state.variant_quantities[variant_key] = new_qty
                    
                    with col4:
                        extracted_compare_prices = variants_data.get('extracted_compare_prices', {})
                        extracted_price = extracted_compare_prices.get(variant_key, 0.0)
                        
                        # Show extracted price directly in input box
                        new_price = st.number_input(
                            "Compare Price", 
                            min_value=0.0, 
                            value=float(extracted_price), 
                            step=0.01,
                            key=f"price_{variant_key}", 
                            label_visibility="collapsed",
                            format="%.2f"
                        )
                        # Update session state with the value
                        st.session_state.variant_compare_prices[variant_key] = new_price
    
    def show_final_statistics(self, df):
        """Show final statistics"""
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<div class="stats-box"><h3>{len(df)}</h3><p>Final Variants</p></div>', unsafe_allow_html=True)
        with col2:
            total_inventory = int(df["Variant Inventory Qty"].sum()) if len(df) > 0 else 0
            st.markdown(f'<div class="stats-box"><h3>{total_inventory}</h3><p>Total Inventory</p></div>', unsafe_allow_html=True)
        with col3:
            unique_products = df["Handle"].nunique() if len(df) > 0 else 0
            st.markdown(f'<div class="stats-box"><h3>{unique_products}</h3><p>Unique Products</p></div>', unsafe_allow_html=True)
        with col4:
            avg_price = df["Variant Price"].replace(0, pd.NA).mean()
            avg_price_text = f"₹{avg_price:.0f}" if pd.notna(avg_price) else "N/A"
            st.markdown(f'<div class="stats-box"><h3>{avg_price_text}</h3><p>Avg Price</p></div>', unsafe_allow_html=True)
    
    def show_tabbed_results(self, df):
        """Show results in tabs"""
        tab1, tab2, tab3 = st.tabs(["📋 Preview", "📈 Summary", "💰 Pricing"])
        
        with tab1:
            st.dataframe(df.head(20), use_container_width=True)
        
        with tab2:
            try:
                summary = df.groupby(["Handle", "Title"]).agg({
                    "Variant Inventory Qty": "sum",
                    "Variant Price": "first"
                }).round(2)
                st.dataframe(summary, use_container_width=True)
            except:
                st.dataframe(df[["Handle", "Title", "Variant Inventory Qty"]], use_container_width=True)
        
        with tab3:
            try:
                price_summary = df[df["Variant Price"] > 0].groupby("Title").agg({
                    "Variant Price": ["min", "max", "mean"]
                }).round(2)
                st.dataframe(price_summary, use_container_width=True)
            except:
                st.dataframe(df[["Title", "Variant Price"]], use_container_width=True)
    
    def render_download_section(self, df):
        """Enhanced download section with step completion"""
        csv_data = df.to_csv(index=False).encode("utf-8")
        
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
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        
        st.success("🎉 Your Shopify CSV is ready!")
        
        with st.expander("💡 Next Steps & Tips"):
            st.markdown("""
            ### 📋 Import to Shopify:
            1. Download your CSV file
            2. Go to Shopify Admin → Products → Import
            3. Upload the CSV file
            4. Review and confirm the import
            
            ### ⚠️ Important Notes:
            - Custom fields and HTML tags are included in descriptions
            - Size surcharges are automatically calculated
            - Inventory quantities are applied from your settings
            - All variants are properly formatted for Shopify
            """)
        
        return True