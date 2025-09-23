# app.py - Main Streamlit Application with Real-time Updates
import os
import time
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# Import our modular components
from backend.ai_service import AIService
from backend.data_processor import DataProcessor
from frontend.ui_components import UIComponents
from helpers.utils import FileHandler, ConfigManager

# Initialize services
load_dotenv()
ai_service = AIService()
data_processor = DataProcessor()
ui_components = UIComponents()
file_handler = FileHandler()
config_manager = ConfigManager()

def main():
    # Page configuration
    st.set_page_config(
        page_title="Shopify Import Builder",
        page_icon="🛍️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Apply custom CSS
    ui_components.apply_custom_css()
    
    # Main header
    ui_components.render_header()
    
    # AI status display
    ui_components.show_ai_status(ai_service.is_enabled())
    
    # Sidebar configuration - CRITICAL: Store in session state for real-time access
    config = ui_components.render_sidebar(ai_service.is_enabled())
    st.session_state.config = config  # Store current config in session state
    
    # Step 1: File Upload
    ui_components.render_step_header("📁 Step 1: Upload Your Product Data")
    uploaded_file = ui_components.render_file_upload()
    
    if not uploaded_file:
        st.info("👆 Please upload a CSV or Excel file to get started")
        return
    
    # Load and preview data
    try:
        df_raw = file_handler.load_file(uploaded_file)
        column_mapping = data_processor.normalize_column_names(df_raw)
        
        # Display file metrics
        ui_components.show_file_metrics(df_raw, column_mapping)
        ui_components.show_data_preview(df_raw, column_mapping)
        
    except Exception as e:
        st.error(f"❌ Could not load file: {e}")
        return
    
    # Step 2: Processing
    ui_components.render_step_header("🚀 Step 2: Process Your Data")
    
    if st.button("🔥 Start Processing", type="primary", use_container_width=True):
        process_data(df_raw, column_mapping, config)
    
    # Step 3: Inventory Management (if data processed)
    if 'processed_data' in st.session_state:
        manage_inventory_and_pricing(config)
    
    # Step 4: Results and Download (if data processed) - REAL-TIME UPDATES
    if 'processed_data' in st.session_state:
        show_results_and_download()

def process_data(df_raw, column_mapping, config):
    """Process the uploaded data with AI enhancement"""
    df = df_raw.copy()
    
    # AI processing with progress bar
    if config['mode'] != "Default template (no AI)":
        df = ai_service.process_descriptions_batch(df, column_mapping, config['mode'])
    
    # Process variants with inventory
    df = data_processor.process_variants_with_inventory(df, column_mapping, config)
    
    # Generate handles
    df = data_processor.generate_handles(df, column_mapping)
    
    # Store in session state
    st.session_state.processed_data = df
    st.session_state.column_mapping = column_mapping
    st.session_state.config = config

def manage_inventory_and_pricing(config):
    """Handle inventory and pricing management UI with real-time updates"""
    ui_components.render_step_header("🧮 Step 3: Manage Inventory & Pricing")
    
    df = st.session_state.processed_data
    column_mapping = st.session_state.column_mapping
    
    # Update config in session state for real-time access
    st.session_state.config = config
    
    # Initialize variant management
    if 'unique_variants_processed' not in st.session_state:
        data_processor.initialize_variant_management(df, column_mapping, config)
    
    # Apply bulk operations if enabled - REAL-TIME
    if config.get('bulk_qty_mode'):
        data_processor.apply_bulk_quantities(config['bulk_qty'])
    
    if config.get('bulk_compare_price_mode'):
        data_processor.apply_bulk_compare_prices(config['bulk_compare_price'])
    
    # Render inventory management interface
    ui_components.render_inventory_management(config)

def show_results_and_download():
    """Display final results and download options with real-time config updates"""
    ui_components.render_step_header("📊 Step 4: Review & Download")
    
    df = st.session_state.processed_data
    column_mapping = st.session_state.column_mapping
    
    # CRITICAL FIX: Always use current config from session state
    config = st.session_state.get('config', {})
    
    # Generate final Shopify CSV with current configuration
    shopify_csv = data_processor.generate_shopify_csv(df, column_mapping, config)
    
    # Show statistics and previews - these will now reflect real-time changes
    ui_components.show_final_statistics(shopify_csv)
    ui_components.show_tabbed_results(shopify_csv)
    
    # Download section
    ui_components.render_download_section(shopify_csv)
    
    # OPTIONAL: Add debug info to verify real-time updates
    with st.expander("🔧 Debug: Current Config", expanded=False):
        st.json(config)
        st.caption("This shows the current configuration being used for generation")

if __name__ == "__main__":
    main()