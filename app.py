# app.py - FIXED: 5-step workflow with AI in sidebar
import os
import streamlit as st
from dotenv import load_dotenv

# Import restructured components
from core.workflow_manager import WorkflowManager
from core.session_manager import SessionManager
from backend.ai_service import AIService
from backend.data_processor import DataProcessor
from frontend.ui_components import UIComponents
from helpers.file_handler import FileHandler

# Load environment variables
load_dotenv()

class ShopifyCSVBuilder:
    """Main application class with 5-step workflow"""
    
    def __init__(self):
        self.workflow = WorkflowManager()
        self.session = SessionManager()
        self.ui = UIComponents()
        self.file_handler = FileHandler()
        self.ai_service = AIService()
        self.data_processor = DataProcessor()
    
    def run(self):
        """Main application entry point with step-based flow"""
        # Initialize page and session
        self._setup_page()
        self.session.initialize()
        
        # Apply styling and render header with progress
        self.ui.apply_styling()
        self.ui.render_header_with_progress()
        self.ui.show_ai_status(self.ai_service.is_enabled())
        
        # Execute step-based workflow
        self._execute_step_workflow()
    
    def _setup_page(self):
        """Configure Streamlit page"""
        st.set_page_config(
            page_title="Shopify Import Builder",
            page_icon="🛍️",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def _execute_step_workflow(self):
        """Execute the 5-step workflow"""
        current_step = self.session.get_current_step()
        
        if current_step == 1:
            self._step_upload()
        elif current_step == 2:
            self._step_mapping()
        elif current_step == 3:
            self._step_description_builder()
        elif current_step == 4:
            self._step_inventory_management()
        elif current_step == 5:
            self._step_generate_csv()
    
    def _step_upload(self):
        """Step 1: File Upload"""
        if not self.workflow.execute_file_upload(self.ui, self.file_handler):
            return
        
        # Navigation
        if self.session.get('df_raw') is not None:
            if st.button("Continue to Column Mapping →", type="primary"):
                self.session.set_current_step(2)
                st.rerun()
    
    def _step_mapping(self):
        """Step 2: Enhanced Column Mapping"""
        if not self.workflow.execute_column_mapping_enhanced(self.ui, self.session):
            return
        
        # Navigation
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back to Upload"):
                self.session.set_current_step(1)
                st.rerun()
        with col2:
            if st.button("Continue to Description Builder →", type="primary"):
                self.session.set_current_step(3)
                st.rerun()
    
    def _step_description_builder(self):
        """Step 3: Dynamic Description Builder"""
        if not self.workflow.execute_description_builder(self.ui, self.session):
            return
        
        # Navigation
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back to Mapping"):
                self.session.set_current_step(2)
                st.rerun()
        with col2:
            if st.button("Continue to Configuration & Inventory →", type="primary"):
                self.session.set_current_step(4)
                st.rerun()
    
    def _step_inventory_management(self):
        """Step 4: Configuration & Inventory Management (AI + Settings)"""
        # Show configuration in sidebar INCLUDING AI mode
        config = self.ui.render_sidebar_config(self.ai_service.is_enabled())
        self.session.update_config(config)
        
        if not self.workflow.execute_inventory_management(self.ui, self.data_processor, self.session):
            return
        
        # Navigation
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back to Description Builder"):
                self.session.set_current_step(3)
                st.rerun()
        with col2:
            if st.button("Generate Shopify CSV →", type="primary"):
                self.session.set_current_step(5)
                st.rerun()
    
    def _step_generate_csv(self):
        """Step 5: Generate Final CSV"""
        # Process AI if enabled before generating CSV
        config = self.session.get_config()
        if config['mode'] != "Default template (no AI)" and self.ai_service.is_enabled():
            # Process with AI before generating CSV
            if self.session.get('processed_data') is None:
                self.workflow.execute_data_processing(self.ui, self.data_processor, self.session)
            
            processed_df = self.session.get('processed_data')
            column_mapping = self.session.get_mappings()
            enhanced_df = self.ai_service.process_descriptions(processed_df, column_mapping, config['mode'])
            self.session.set('processed_data', enhanced_df)
        
        # Generate CSV
        if not self.workflow.execute_csv_generation(self.ui, self.data_processor, self.session):
            return

def main():
    """Application entry point"""
    try:
        app = ShopifyCSVBuilder()
        app.run()
    except Exception as e:
        st.error(f"⚠️ Application Error: {str(e)}")
        with st.expander("🔧 Debug Information", expanded=False):
            st.code(f"Error: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    main()