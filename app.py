# streamlit_app.py
import os, time, json
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai
import numpy as np

# ── 1) Init GenAI Client ────────────────────────────────────────────────────
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

# ── Helper Functions ────────────────────────────────────────────────────────
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

def parse_size_and_quantity(size_string):
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
            import re
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

def process_variants_with_inventory(df_raw):
    """Process variants and extract both inventory quantities and compare prices from uploaded data"""
    df_exploded_list = []
    
    # Get column mapping for case-insensitive access
    column_mapping = normalize_column_names(df_raw)
    
    for _, row in df_raw.iterrows():
        # Parse sizes and extract quantities using normalized column access
        sizes_value = get_column_value(row, column_mapping, 'size', "")
        colours_value = get_column_value(row, column_mapping, 'colour', "")
        
        sorted_sizes, size_quantity_map = sort_sizes_with_quantities(clean_value(sizes_value))
        colors = [c.strip() for c in str(clean_value(colours_value)).split(",") if c.strip()]
        
        # Extract compare price from uploaded data (case insensitive)
        uploaded_compare_price = default_compare_price
        
        # Try to get compare price using normalized column mapping
        compare_price_value = get_column_value(row, column_mapping, 'variant compare at price')
        if compare_price_value and pd.notna(compare_price_value) and str(compare_price_value).strip() != '':
            try:
                numeric_value = float(str(compare_price_value).strip())
                if numeric_value >= 0:
                    uploaded_compare_price = numeric_value
            except (ValueError, TypeError):
                pass
        
        # If no sizes or colors, create default entries
        if not sorted_sizes:
            sorted_sizes = [""]
            size_quantity_map = {"": 0}
        if not colors:
            colors = [""]
        
        # Create all combinations
        for size in sorted_sizes:
            for color in colors:
                new_row = row.copy()
                new_row["sizes_list"] = size  # Just the size (S, M, L, XL)
                new_row["colours_list"] = color
                new_row["extracted_quantity"] = size_quantity_map.get(size, 0)  # Extracted quantity
                new_row["uploaded_compare_price"] = uploaded_compare_price  # Extracted compare price
                df_exploded_list.append(new_row)
    
    return pd.DataFrame(df_exploded_list)

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
    if fabric: specs.append(f"<li><strong>Fabric</strong>: {fabric}</li>")
    if celebs_name: specs.append(f"<li><strong>Celebs Name</strong>: {celebs_name}</li>")
    if no_of_components: specs.append(f"<li><strong>No of components (set)</strong>: {no_of_components}</li>")
    if colors: specs.append(f"<li><strong>Color</strong>: {colors}</li>")
    if product_code: specs.append(f"<li><strong>SKU</strong>: {product_code}</li>")
    if fit: specs.append(f"<li><strong>Fit</strong>: {fit}</li>")
    if sizes_info: specs.append(f"<li><strong>Sizes (surcharges if any)</strong>: {sizes_info}</li>")
    if delivery_time: specs.append(f"<li><strong>Delivery Time</strong>: {delivery_time}</li>")
    if wash_care: specs.append(f"<li><strong>Wash Care</strong>: {wash_care}</li>")
    if technique_used: specs.append(f"<li><strong>Technique Used</strong>: {technique_used}</li>")
    if embroidery_details: specs.append(f"<li><strong>Embroidery Details</strong>: {embroidery_details}</li>")

    if specs:
        html_parts.append("<ul>" + "".join(specs) + "</ul>")

    return "".join(html_parts) if html_parts else ""

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

def tags_only(text: str) -> str:
    """Generate tags from text using AI (simple mode)"""
    if not ai_enabled:
        return ""
    
    prompt = (
        "Extract exactly 5 relevant product tags from this text. "
        "Return only the tags as a comma-separated list with no extra text.\n\n"
        f"Text: {text}\n\n"
        "Tags:"
    )
    
    try:
        response = model.generate_content(prompt)
        return (response.text or "").strip()
    except Exception as e:
        st.warning(f"AI tag generation failed: {e}")
        return ""

# ── 2) Enhanced UI Setup ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Shopify Import Builder", 
    page_icon="🛍️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
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
</style>
""", unsafe_allow_html=True)

# Main Header
st.markdown("""
<div class="main-header">
    <h1>🛍️ Advanced Shopify CSV Builder</h1>
    <p>Transform your product data into Shopify-ready imports with AI-powered descriptions and smart inventory management</p>
</div>
""", unsafe_allow_html=True)

# AI Status Check
if not GEMINI_API_KEY:
    st.markdown('<div class="ai-status ai-disabled">⚠️ AI Features Disabled - Missing GEMINI_API_KEY</div>', unsafe_allow_html=True)
    ai_enabled = False
else:
    st.markdown('<div class="ai-status ai-enabled">✅ AI Features Enabled - Gemini 2.5 Flash Ready</div>', unsafe_allow_html=True)
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    ai_enabled = True

# ── 3) Enhanced Sidebar Configuration ──────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    
    # Processing mode selection
    mode = st.radio(
        "🤖 AI Processing Mode:",
        options=[
            "Default template (no AI)",
            "Simple mode (first sentence + tags)",
            "Full AI mode (custom description + tags)"
        ],
        index=0 if not ai_enabled else 0,
        disabled=not ai_enabled,
        help="Choose how you want to process product descriptions"
    )
    
    st.markdown("---")
    
    st.markdown("### ➕ Size Surcharge Settings")
    enable_surcharge = st.checkbox("Enable Size Surcharge")

    surcharge_rules = {}

    if enable_surcharge:
        st.caption("Add sizes (greater than XL) with surcharge %")
        
        # number of surcharge rules to add
        num_rules = st.number_input(
            "How many size surcharges?",
            min_value=1, value=1, step=1, key="num_surcharge_rules"
        )
        
        for i in range(num_rules):
            cols = st.columns([2, 1])
            with cols[0]:
                size = st.text_input(f"Size {i+1}", key=f"surcharge_size_{i}").upper().strip()
            with cols[1]:
                percent = st.number_input(
                    f"%", min_value=0.0, value=0.0, step=0.5, key=f"surcharge_percent_{i}"
                )
            
            if size and percent > 0:
                surcharge_rules[size] = percent / 100.0
                
    st.markdown("---")
    
    # Brand customization
    st.markdown("### 🏢 Brand Settings")
    vendor_name = st.text_input("Vendor Name", value="YourBrandName", help="This will appear as the vendor in Shopify")
    
    # Inventory settings (simplified)
    st.markdown("### 📦 Inventory Settings")
    inventory_policy = st.selectbox(
        "Inventory Policy",
        options=["deny", "continue"],
        index=0,
        help="continue = Allow sales when out of stock, deny = Stop sales when out of stock"
    )
    
    default_qty = st.number_input(
        "Fallback Quantity", 
        min_value=0, 
        value=10, 
        step=1,
        help="Used when no quantity is found in size data"
    )
    
    bulk_qty_mode = st.checkbox(
        "Override with Bulk Quantity", 
        help="Ignore extracted quantities and set same quantity for all variants"
    )
    
    if bulk_qty_mode:
        bulk_qty = st.number_input("Bulk Quantity", min_value=0, value=default_qty, step=1)
    
    # Price settings (simplified)
    st.markdown("### 💰 Price Settings")
    default_compare_price = st.number_input(
        "Default Compare At Price", 
        min_value=0.0, 
        value=0.0, 
        step=0.01, 
        format="%.2f"
    )
    
    bulk_compare_price_mode = st.checkbox(
        "Enable Bulk Compare Price", 
        help="Set same compare price for all variants"
    )
    
    if bulk_compare_price_mode:
        bulk_compare_price = st.number_input(
            "Bulk Compare Price", 
            min_value=0, 
            value=default_compare_price, 
            step=0.01, 
            format="%.2f"
        )
    
    st.markdown("---")
    
    # Enhanced file format info
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
        
        **Size Format Examples:**
        - `S-4,M-8,L-12,XL-16` → Sizes: S,M,L,XL with Quantities: 4,8,12,16
        - `XS-0,S-5,M-10,L-15,XL-20` → Auto-extracts quantities
        - `Custom,Small,Medium,Large` → Uses fallback quantity
        
        **Note:** Column names are now case-insensitive and support common variations!
        """)
    
    # Processing tips
    with st.expander("💡 Processing Tips", expanded=False):
        st.markdown("""
        **How it works:**
        1. **Case Insensitive**: Handles `Title`, `TITLE`, `title` - all work!
        2. **Size Parsing**: `S-4` becomes Size=`S`, Quantity=`4`
        3. **Smart Sorting**: Sizes ordered as XS, S, M, L, XL, XXL, etc.
        4. **Manual Override**: You can adjust any extracted quantities
        5. **Bulk Options**: Override extracted quantities if needed
        6. **Components & Fabric**: Added as custom properties for better product info
        
        **Best Practices:**
        - Column names can be in any case (Title, TITLE, title all work)
        - Use consistent size format: `SIZE-QUANTITY`
        - Check extracted quantities before processing
        - Use bulk mode only when you want same qty for all
        - Fill in fabric and components data for better product details
        """)

# ── 4) File Upload Section ──────────────────────────────────────────────────
st.markdown('<div class="step-header"><h2>📁 Step 1: Upload Your Product Data</h2></div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([200, 1, 1])

with col1:
    uploaded_file = st.file_uploader(
        "Choose your CSV or Excel file",
        type=["csv", "xlsx"],
        help="Upload a file containing your product data"
    )

with col2:
    if uploaded_file:
        file_size = len(uploaded_file.getvalue()) / 1024  # KB
        st.metric("File Size", f"{file_size:.1f} KB")

with col3:
    if uploaded_file:
        file_type = "Excel" if uploaded_file.name.lower().endswith(".xlsx") else "CSV"
        st.metric("File Type", file_type)

if not uploaded_file:
    st.info("👆 Please upload a CSV or Excel file to get started")
    st.stop()

# ── 5) Load & Preview Data ──────────────────────────────────────────────────
try:
    df_raw = pd.read_excel(uploaded_file) if uploaded_file.name.lower().endswith(".xlsx") else pd.read_csv(uploaded_file)
    
    # Get column mapping for case-insensitive processing
    column_mapping = normalize_column_names(df_raw)
    
    # Display success metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="stats-box"><h3>{}</h3><p>Total Products</p></div>'.format(len(df_raw)), unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="stats-box"><h3>{}</h3><p>Columns</p></div>'.format(len(df_raw.columns)), unsafe_allow_html=True)
    with col3:
        # Calculate total variants using safe column access
        total_variants = 0
        for _, row in df_raw.iterrows():
            sizes_value = get_column_value(row, column_mapping, 'size', "")
            colours_value = get_column_value(row, column_mapping, 'colour', "")
            size_count = len([s.strip() for s in str(sizes_value).split(',') if s.strip()]) if sizes_value else 1
            color_count = len([c.strip() for c in str(colours_value).split(',') if c.strip()]) if colours_value else 1
            total_variants += size_count * color_count
        st.markdown('<div class="stats-box"><h3>{}</h3><p>Est. Variants</p></div>'.format(total_variants), unsafe_allow_html=True)
    with col4:
        # Count active products using safe column access
        active_products = 0
        for _, row in df_raw.iterrows():
            published_value = get_column_value(row, column_mapping, 'published', "")
            if str(published_value).lower() == 'active':
                active_products += 1
        st.markdown('<div class="stats-box"><h3>{}</h3><p>Active Products</p></div>'.format(active_products), unsafe_allow_html=True)
    
    # Check for missing or zero variant prices in uploaded data (case insensitive)
    price_column_actual = column_mapping.get('variant price')
    if not price_column_actual:
        # Fallback to direct search
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
            st.warning(f"⚠️ **PRICE ALERT**: {total_products_with_zero_prices} out of {len(df_raw)} products have missing or zero prices in the '{price_column_actual}' column. Please update your source data with proper pricing before processing to avoid Shopify import issues.")
    
    # Show column mapping information
    if column_mapping:
        with st.expander("🔍 Detected Column Mappings", expanded=False):
            st.write("The following columns were automatically detected (case-insensitive):")
            for standard_name, actual_column in column_mapping.items():
                st.write(f"**{standard_name}** → `{actual_column}`")
    
    # Data preview with tabs
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

except Exception as e:
    st.error(f"❌ Could not load file: {e}")
    st.stop()

# ── 6) AI Helper Functions ──────────────────────────────────────────────────

def refine_and_tag(text: str) -> tuple[str, str]:
    if not ai_enabled:
        return text, ""

    prompt = (
        "You are a top-tier Shopify copywriter.\n"
        "1) Rewrite this product description to be clear, engaging, and on-brand.\n"
        "2) Then output on the next line exactly five comma-separated tags.\n\n"
        f"Original description:\n\"\"\"\n{text}\n\"\"\"\n\n"
        "Respond with exactly two lines:\n"
        "- Line 1: your rewritten description\n"
        "- Line 2: tag1,tag2,tag3,tag4,tag5"
    )

    try:
        response = model.generate_content(prompt)
        return (response.text or "").strip()
    except Exception as e:
        st.warning(f"⚠️ AI tag generation failed: {e}")
        return ""

# ── 7) Processing Section ──────────────────────────────────────────────────
st.markdown('<div class="step-header"><h2>🚀 Step 2: Process Your Data</h2></div>', unsafe_allow_html=True)

process_button = st.button("🔄 Start Processing", type="primary", use_container_width=True)
if process_button or 'processed_data' in st.session_state:
    
    # Only do AI processing if button was clicked (not on rerun)
    if process_button:
        df = df_raw.copy()
        n = len(df)
        
        # Processing progress with detailed status
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
            custom_descs, all_tags = [], []

            with st.spinner("🔮 AI is working its magic..."):
                for i, (_, row) in enumerate(df.iterrows()):
                    # Use normalized column access for title and description
                    title = get_column_value(row, column_mapping, 'title', 'Unknown')
                    if pd.isna(title) or title is None:
                        title = 'Unknown'
                    status_text.text(f"Processing product {i+1}/{n}: {str(title)[:30]}...")
                    
                    original = clean_value(get_column_value(row, column_mapping, 'description', ""))
                    if mode == "Default template (no AI)":
                        desc = original
                        tags = ""
                    elif mode == "Simple mode (first sentence + tags)":
                        first_sent = original.split(".", 1)[0].strip()
                        desc = first_sent
                        tags = tags_only(first_sent)
                    else:
                        desc, tags = refine_and_tag(original)

                    custom_descs.append(desc)
                    all_tags.append(tags)
                    progress_bar.progress((i + 1) / n)
                    time.sleep(0.1)  # Reduced sleep time

            status_text.text("✅ AI processing complete!")

        df["custom_description"] = custom_descs
        df["ai_tags"] = all_tags

        # Process variants with extracted inventory quantities
        df = process_variants_with_inventory(df)
        
        # ── Corrected Handle Generation using normalized column access ──
        title_series = safe_get_column_data(df, column_mapping, 'title', 'Unknown')
        product_code_series = safe_get_column_data(df, column_mapping, 'product code', '')
        
        # Generate handles based on title + sku combination
        df["Handle"] = (title_series.astype(str).fillna("").str.strip() + "-" + 
                        product_code_series.fillna("").astype(str).str.strip())

        # Clean handles for Shopify format
        df["Handle"] = (df["Handle"]
                        .str.replace(r"[^\w\s-]", "", regex=True)
                        .str.replace(r"\s+", "-", regex=True)
                        .str.lower()
                        .str.replace(r"-+", "-", regex=True)
                        .str.strip("-"))                           
        
        # Store processed data in session state
        st.session_state.processed_data = df
        st.session_state.column_mapping = column_mapping  # Store column mapping
        st.session_state.variant_quantities = {}
        st.session_state.variant_compare_prices = {}
    else:
        # Use existing processed data
        df = st.session_state.processed_data
        column_mapping = st.session_state.column_mapping

    # ── 8) Enhanced Inventory and Compare Price Management ──────────────────────
    st.markdown('<div class="step-header"><h2>🧮 Step 3: Manage Inventory & Pricing</h2></div>', unsafe_allow_html=True)
    
    if 'unique_variants_processed' not in st.session_state:
        unique_variants = []
        variant_products = {}
        extracted_quantities = {}
        extracted_compare_prices = {}  # Initialize here
        
        # Group by handle first, then get variants
        for handle, group in df.groupby("Handle"):
            # Get product title using normalized column access from first row
            first_row = group.iloc[0]
            title = clean_value(get_column_value(first_row, column_mapping, 'title', 'Unknown'))
            
            for _, row in group.iterrows():
                size = clean_value(row['sizes_list'])
                color = clean_value(row['colours_list'])
                extracted_qty = row.get('extracted_quantity', 0)
                extracted_compare_price = row.get('uploaded_compare_price', default_compare_price)
                
                variant_key = (size, color, title)
                if variant_key not in unique_variants:
                    unique_variants.append(variant_key)
                    variant_products[variant_key] = title
                    extracted_quantities[variant_key] = extracted_qty
                    extracted_compare_prices[variant_key] = extracted_compare_price
        
        # Store ALL variables in session state at once
        st.session_state.unique_variants = unique_variants
        st.session_state.variant_products = variant_products
        st.session_state.extracted_quantities = extracted_quantities
        st.session_state.extracted_compare_prices = extracted_compare_prices  # Store in session state
        st.session_state.unique_variants_processed = True
    else:
        # Load ALL variables from session state
        unique_variants = st.session_state.unique_variants
        variant_products = st.session_state.variant_products
        extracted_quantities = st.session_state.extracted_quantities
        extracted_compare_prices = st.session_state.extracted_compare_prices

    if 'variant_quantities' not in st.session_state:
        st.session_state.variant_quantities = {}
        for size, color, title in unique_variants:
            variant_key = f"{size}|{color}|{title}"
            extracted_qty = extracted_quantities.get((size, color, title), 0)
            st.session_state.variant_quantities[variant_key] = extracted_qty if extracted_qty > 0 else default_qty

    if 'variant_compare_prices' not in st.session_state:
        st.session_state.variant_compare_prices = {}
        for size, color, title in unique_variants:
            variant_key = f"{size}|{color}|{title}"
            extracted_compare_price = extracted_compare_prices.get((size, color, title), default_compare_price)
            st.session_state.variant_compare_prices[variant_key] = extracted_compare_price

    if enable_surcharge:
        for size, color, title in unique_variants:
            variant_key = f"{size}|{color}|{title}"
            try:
                # Use safe column access for variant price
                matching_rows = df[
                    (df["sizes_list"] == size) &
                    (df["colours_list"] == color) &
                    (safe_get_column_data(df, column_mapping, 'title', 'Unknown') == title)
                ]
                if not matching_rows.empty:
                    base_price = float(safe_get_column_data(matching_rows, column_mapping, 'variant price', 0).iloc[0])
                else:
                    base_price = 0.0
            except Exception:
                base_price = 0.0

            if size.upper().strip() in surcharge_rules:
                new_compare = round(base_price * (1 + surcharge_rules[size.upper().strip()]), 2)
                st.session_state.variant_compare_prices[variant_key] = new_compare
                    
    for size, color, title in unique_variants:
        variant_key = f"{size}|{color}|{title}"
        extracted_qty = extracted_quantities.get((size, color, title), 0)
        
        if extracted_qty > 0:
            current_value = st.session_state.variant_quantities.get(variant_key, default_qty)
            if current_value == default_qty or variant_key not in st.session_state.variant_quantities:
                st.session_state.variant_quantities[variant_key] = extracted_qty
                
    for size, color, title in unique_variants:
        variant_key = f"{size}|{color}|{title}"
        extracted_compare_price = extracted_compare_prices.get((size, color, title), default_compare_price)
        if extracted_compare_price > 0 and extracted_compare_price != default_compare_price:
            current_value = st.session_state.variant_compare_prices.get(variant_key, default_compare_price)
            if current_value == default_compare_price or variant_key not in st.session_state.variant_compare_prices:
                st.session_state.variant_compare_prices[variant_key] = extracted_compare_price

    if bulk_qty_mode:
        st.info(f"📦 Bulk mode enabled: Setting {bulk_qty} for all variants")
        for size, color, title in unique_variants:
            variant_key = f"{size}|{color}|{title}"
            st.session_state.variant_quantities[variant_key] = bulk_qty

    if bulk_compare_price_mode:
        st.info(f"💰 Bulk compare price mode enabled: Setting ₹{bulk_compare_price:.2f} for all variants")
        for size, color, title in unique_variants:
            variant_key = f"{size}|{color}|{title}"
            st.session_state.variant_compare_prices[variant_key] = bulk_compare_price

    # Manual editing interface (enhanced)
    if not bulk_qty_mode or not bulk_compare_price_mode:
        if 'products_variants_grouped' not in st.session_state:
            products_variants = {}
            for size, color, title in unique_variants:
                if title not in products_variants:
                    products_variants[title] = []
                products_variants[title].append((size, color))
            st.session_state.products_variants_grouped = products_variants
        else:
            products_variants = st.session_state.products_variants_grouped
        
        st.markdown("### 🔧 Individual Variant Management")
        for product_title, variants in products_variants.items():
            total_qty = 0
            total_variants = len(variants)
            
            for size, color in variants:
                variant_key = f"{size}|{color}|{product_title}"
                total_qty += st.session_state.variant_quantities.get(variant_key, 0)
            
            with st.expander(f"📦 {product_title} ({total_variants} variants, {total_qty} total qty)", expanded=len(products_variants) <= 3):
                
                # Use form for batch updates per product
                with st.form(key=f"form_{hash(product_title) % 10000}"):
                    
                    variant_inputs = {}
                    for idx, (size, color) in enumerate(variants):
                        variant_key = f"{size}|{color}|{product_title}"
                        current_qty = st.session_state.variant_quantities.get(variant_key, default_qty)
                        current_compare_price = st.session_state.variant_compare_prices.get(variant_key, default_compare_price)
                        
                        extracted_qty = extracted_quantities.get((size, color, product_title), 0)
                        extracted_compare_price = extracted_compare_prices.get((size, color, product_title), default_compare_price)

                        col1, col2, col3 = st.columns([2, 2, 2])

                        with col1:
                            st.markdown(f"**{size} / {color if color else 'N/A'}**")
                            if extracted_qty > 0:
                                st.caption(f"↗️ Extracted Qty: {extracted_qty}")
                            if extracted_compare_price > 0 and extracted_compare_price != default_compare_price:
                                st.caption(f"💰 Extracted Compare: ₹{extracted_compare_price:.2f}")

                        with col2:
                            current_qty = st.session_state.variant_quantities.get(variant_key, default_qty)
                            qty = st.number_input(
                                f"Quantity",
                                min_value=0, 
                                value=int(current_qty),
                                step=1, 
                                key=f"form_qty_{variant_key}_{hash(variant_key) % 10000}",
                                help=f"Extracted from size data: {extracted_qty}" if extracted_qty > 0 else "Manual quantity"
                            )

                        with col3:
                            current_compare_price = st.session_state.variant_compare_prices.get(variant_key, default_compare_price)
                            compare_price = st.number_input(
                                f"Compare Price (₹)",
                                min_value=0.0,
                                value=float(current_compare_price),
                                step=1.0,
                                format="%.2f",
                                key=f"form_price_{variant_key}_{hash(variant_key) % 10000}",
                                help=f"Extracted from uploaded data: ₹{extracted_compare_price:.2f}" if extracted_compare_price != default_compare_price else "Manual compare price"
                            )

                        variant_inputs[variant_key] = (qty, compare_price)
                    
                    # Submit button for this product
                    if st.form_submit_button(f"💾 Update {product_title}", use_container_width=True):
                        for variant_key, (qty, compare_price) in variant_inputs.items():
                            st.session_state.variant_quantities[variant_key] = qty
                            st.session_state.variant_compare_prices[variant_key] = compare_price
                        st.success(f"✅ Updated quantities and prices for {product_title}")
        
        with st.expander("⚡ Power User: Spreadsheet-Style Editing", expanded=False):
            st.markdown("*Excel-like interface for bulk editing*")
            
            # Create a dataframe for editing
            variant_data = []
            for size, color, title in unique_variants:
                variant_key = f"{size}|{color}|{title}"
                extracted_qty = extracted_quantities.get((size, color, title), 0)
                extracted_compare_price = extracted_compare_prices.get((size, color, title), default_compare_price)
                
                current_qty = st.session_state.variant_quantities.get(variant_key, default_qty)
                current_compare_price = st.session_state.variant_compare_prices.get(variant_key, default_compare_price)
                
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
                    'Extracted Qty': st.column_config.NumberColumn('Extracted Qty', disabled=True, help="Quantity extracted from size data"),
                    'Current Qty': st.column_config.NumberColumn('Current Qty', min_value=0, step=1),
                    'Extracted Compare Price': st.column_config.NumberColumn('Extracted Compare Price (₹)', disabled=True, format="%.2f", help="Compare price from uploaded data"),
                    'Current Compare Price': st.column_config.NumberColumn('Current Compare Price (₹)', min_value=0.0, step=0.01, format="%.2f")
                }
            )
            
            if st.button("💾 Apply All Spreadsheet Changes", key="apply_table", type="primary"):
                for i, variant_key in enumerate(variant_df['Key']):
                    st.session_state.variant_quantities[variant_key] = int(edited_variants.iloc[i]['Current Qty'])
                    st.session_state.variant_compare_prices[variant_key] = float(edited_variants.iloc[i]['Current Compare Price'])
                st.success("✅ Applied all spreadsheet changes!")
                st.rerun()

    # Apply quantities and compare prices to dataframe - FIXED VERSION with case-insensitive access
    variant_qty_map = st.session_state.variant_quantities
    variant_compare_price_map = st.session_state.variant_compare_prices
    
    # Create variant key for mapping using normalized column access
    title_series = safe_get_column_data(df, column_mapping, 'title', 'Unknown')
    df["_variant_key"] = (df["sizes_list"].astype(str).fillna("").str.strip() + "|" + 
                         df["colours_list"].astype(str).fillna("").str.strip() + "|" + 
                         title_series.astype(str).fillna("").str.strip())
    
    def get_quantity(variant_key):
        return variant_qty_map.get(variant_key, default_qty)
    
    def get_final_compare_price(row):
        # Use safe column access for variant price
        base_price = 0
        try:
            variant_price_value = get_column_value(row, column_mapping, 'variant price', 0)
            base_price = clean_value(variant_price_value, is_numeric=True, default_numeric=0)
        except:
            base_price = 0
            
        size = str(row["sizes_list"]).upper().strip()

        # If surcharge enabled and size matches → apply on Variant Price
        if enable_surcharge and size in surcharge_rules:
            return round(base_price * (1 + surcharge_rules[size]), 2)

        # Otherwise → fall back to the base Compare At Price (from sheet/default)
        return row["Variant Compare At Price"]
    
    if "variant_compare_prices" not in st.session_state:
        st.session_state.variant_compare_prices = {}

    for _, row in df.iterrows():
        variant_key = row["_variant_key"]
        st.session_state.variant_compare_prices[variant_key] = float(row["Variant Compare At Price"])

    df["Variant Inventory Qty"] = df["_variant_key"].apply(get_quantity)
    df["Variant Compare At Price"] = df.apply(get_final_compare_price, axis=1)
    df["Variant Inventory Qty"] = pd.to_numeric(df["Variant Inventory Qty"], errors='coerce').fillna(0).astype(int)
    df["Variant Compare At Price"] = pd.to_numeric(df["Variant Compare At Price"], errors='coerce').fillna(default_compare_price).astype(float)

    grouped_data = []

    for handle, group in df.groupby("Handle"):
        sizes_in_group = group['sizes_list'].unique()
        
        sorted_sizes_for_group = []
        if len(sizes_in_group) > 0:
            sizes_string = ','.join(sizes_in_group)
            sorted_sizes_for_group = sort_sizes(sizes_string)
        
        size_order_map = {size: idx for idx, size in enumerate(sorted_sizes_for_group)}
        
        def sort_key(row):
            size = row['sizes_list']
            color = row['colours_list']
            size_idx = size_order_map.get(size, 999)  # Unknown sizes go to end
            return (size_idx, color)
        
        group_list = list(group.iterrows())
        group_list.sort(key=lambda x: sort_key(x[1]))

        processed_rows = []
        for orig_idx, row in group_list:
            variant_key = f"{row['sizes_list']}|{row['colours_list']}|{get_column_value(row, column_mapping, 'title', 'Unknown')}"
            updated_row = row.copy()
            
            if variant_key in st.session_state.variant_quantities:
                updated_row['Variant Inventory Qty'] = st.session_state.variant_quantities[variant_key]
            if variant_key in st.session_state.variant_compare_prices:
                updated_row['Variant Compare At Price'] = st.session_state.variant_compare_prices[variant_key]
            
            processed_rows.append(updated_row)
        
        # Get product-level information from first row using normalized column access
        first_row = processed_rows[0]
        has_colors = any(clean_value(row["colours_list"]) for row in processed_rows)
        first_variant = {
            "Handle": clean_value(handle),
            "Title": clean_value(get_column_value(first_row, column_mapping, 'title', 'Unknown')),
            "Body (HTML)": generate_structured_body_html(first_row, column_mapping),
            "Vendor": vendor_name,
            "Product Category": clean_value(get_column_value(first_row, column_mapping, 'product category', '')),
            "Type": clean_value(get_column_value(first_row, column_mapping, 'type', '')),
            "Fabric": clean_value(get_column_value(first_row, column_mapping, 'fabric', '')),
            "Tags": clean_value(first_row["ai_tags"]),
            "Published": "TRUE" if str(clean_value(get_column_value(first_row, column_mapping, 'published', ''))).lower() == "active" else "FALSE",
            "Option1 Name": "Size",
            "Option1 Value": clean_value(first_row["sizes_list"]),
            "Option2 Name": "Color" if has_colors else "",
            "Option2 Value": clean_value(first_row["colours_list"]),
            "Option3 Name": "",
            "Option3 Value": "",
            "Variant SKU": f"{clean_value(get_column_value(first_row, column_mapping, 'product code', ''))}",
            "Variant Grams": clean_value(0, is_numeric=True),
            "Variant Inventory Tracker": "",
            "Variant Inventory Qty": clean_value(first_row["Variant Inventory Qty"], is_numeric=True),
            "Variant Inventory Policy": inventory_policy,
            "Variant Fulfillment Service": "manual",
            "Variant Compare At Price": clean_value(first_row["Variant Compare At Price"], is_numeric=True),
            "Variant Price": clean_value(get_column_value(first_row, column_mapping, 'variant price', 0), is_numeric=True),
            "Variant Requires Shipping": "TRUE",
            "Variant Taxable": "TRUE",
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
            "Cost per item": clean_value(0, is_numeric=True),
            "Status": clean_value(first_row.get("Status", "active"))
        }
        
        grouped_data.append(first_variant)
        
        for _, row in group_list[1:]:
            variant_row = {
                "Handle": clean_value(handle),
                "Title": "", 
                "Body (HTML)": "",
                "Vendor": "",
                "Product Category": "",
                "Type": "",
                "Fabric": "",
                "Tags": "",
                "Published": "",
                "Option1 Name": "",
                "Option1 Value": clean_value(row["sizes_list"]),
                "Option2 Name": "",
                "Option2 Value": clean_value(row["colours_list"]),
                "Option3 Name": "",
                "Option3 Value": "",
                "Variant SKU": f"{clean_value(get_column_value(row, column_mapping, 'product code', ''))}",
                "Variant Grams": clean_value(0, is_numeric=True),
                "Variant Inventory Tracker": "",
                "Variant Inventory Qty": clean_value(row["Variant Inventory Qty"], is_numeric=True),
                "Variant Inventory Policy": inventory_policy,
                "Variant Fulfillment Service": "manual",
                "Variant Compare At Price": clean_value(row["Variant Compare At Price"], is_numeric=True),
                "Variant Price": clean_value(get_column_value(row, column_mapping, 'variant price', 0), is_numeric=True),
                "Variant Requires Shipping": "TRUE",
                "Variant Taxable": "TRUE",
                "Image Src": "",
                "Image Position": "",
                "Image Alt Text": "",
                "Gift Card": "",
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
                "Cost per item": clean_value(0, is_numeric=True),
                "Status": "" 
            }
            grouped_data.append(variant_row)

    # Create the final output dataframe
    out = pd.DataFrame(grouped_data)
    
    # Final cleanup to ensure no NaN values in output
    for col in out.columns:
        if out[col].dtype == 'object':  # String columns
            out[col] = out[col].fillna('').astype(str)
            out[col] = out[col].replace(['nan', 'NaN', 'None'], '')
        else:  # Numeric columns
            out[col] = out[col].fillna(0)

    # ── 9) Results Display ──────────────────────────────────────────────────
    st.markdown('<div class="step-header"><h2>📊 Step 4: Review & Download</h2></div>', unsafe_allow_html=True)
    
    # Final statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="stats-box"><h3>{}</h3><p>Final Variants</p></div>'.format(len(out)), unsafe_allow_html=True)
    with col2:
        total_inventory = int(out["Variant Inventory Qty"].sum()) if len(out) > 0 else 0
        st.markdown('<div class="stats-box"><h3>{}</h3><p>Total Inventory</p></div>'.format(total_inventory), unsafe_allow_html=True)
    with col3:
        unique_products = out["Handle"].nunique() if len(out) > 0 else 0
        st.markdown('<div class="stats-box"><h3>{}</h3><p>Unique Products</p></div>'.format(unique_products), unsafe_allow_html=True)
    with col4:
        avg_price = out["Variant Price"].replace(0, pd.NA).mean()
        st.markdown('<div class="stats-box"><h3>{}</h3><p>Avg Price</p></div>'.format(f"₹{avg_price:.0f}" if pd.notna(avg_price) else "N/A"), unsafe_allow_html=True)

    # Tabbed results view - Updated with new columns
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Final Preview", "📈 Inventory Summary", "🏷️ AI Tags Overview", "💰 Price Summary", "🧵 Product Details"])
    
    with tab1:
        st.dataframe(out.head(20), use_container_width=True)
    
    with tab2:
        try:
            inventory_summary = out.groupby(["Handle", "Title"]).agg({
                "Variant Inventory Qty": ["sum", "count"],
                "Variant Price": "first",
                "Variant Compare At Price": "first"
            }).round(2)
            inventory_summary.columns = ["Total Qty", "Variants", "Price", "Compare Price"]
            st.dataframe(inventory_summary, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating inventory summary: {e}")
            st.dataframe(out[["Handle", "Title", "Variant Inventory Qty", "Variant Price", "Variant Compare At Price"]], use_container_width=True)
    
    with tab3:
        if ai_enabled and mode != "Default template (no AI)":
            tags_df = out[out["Tags"] != ""][["Title", "Tags"]].drop_duplicates()
            if len(tags_df) > 0:
                st.dataframe(tags_df, use_container_width=True)
            else:
                st.info("No AI tags generated")
        else:
            st.info("No AI tags generated in current mode")
    
    with tab4:
        try:
            price_summary = out[out["Variant Price"] > 0].groupby(["Handle", "Title"]).agg({
                "Variant Price": ["min", "max", "mean"],
                "Variant Compare At Price": ["min", "max", "mean"]
            }).round(2)
            price_summary.columns = ["Min Price", "Max Price", "Avg Price", "Min Compare", "Max Compare", "Avg Compare"]
            st.dataframe(price_summary, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating price summary: {e}")
            st.dataframe(out[["Handle", "Title", "Variant Price", "Variant Compare At Price"]], use_container_width=True)
    
    with tab5:
        try:
            details_df = out[out["Title"] != ""][["Title", "No of Components", "Fabric", "Type", "Product Category"]].drop_duplicates()
            if len(details_df) > 0:
                st.dataframe(details_df, use_container_width=True)
                
                # Show fabric and components statistics
                if not details_df["Fabric"].str.strip().eq("").all():
                    st.markdown("#### 🧵 Fabric Types:")
                    fabric_counts = details_df["Fabric"].value_counts()
                    fabric_counts = fabric_counts[fabric_counts.index != ""]  # Remove empty values
                    if len(fabric_counts) > 0:
                        st.bar_chart(fabric_counts)
                
                if not details_df["No of Components"].str.strip().eq("").all():
                    st.markdown("#### 🔢 Components Distribution:")
                    component_counts = details_df["No of Components"].value_counts()
                    component_counts = component_counts[component_counts.index != ""]  # Remove empty values
                    if len(component_counts) > 0:
                        st.bar_chart(component_counts)
            else:
                st.info("No product details available")
        except Exception as e:
            st.error(f"Error creating details summary: {e}")

    # Download section
    csv_data = out.to_csv(index=False).encode("utf-8")
    
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
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Success message
    st.success("🎉 Your Shopify CSV is ready! The file contains all variants with extracted inventory quantities, compare prices, components, and fabric information.")
    
    # Usage tips
    with st.expander("💡 Next Steps & Tips"):
        st.markdown("""
        ### 📋 What to do next:
        1. **Download** your CSV file using the button above
        2. **Review** the data in Excel/Google Sheets if needed
        3. **Import** to Shopify via: Products → Import
        4. **Check** that all variants imported correctly
        
        ### ⚠️ Important Notes:
        - Make sure your Shopify store accepts the product categories used
        - Verify that all image URLs (if any) are accessible
        - Double-check pricing and inventory levels
        - Test with a small batch first if you have many products
        - Sizes are automatically sorted: XS, S, M, L, XL, XXL, XXXL, then custom sizes
        """)