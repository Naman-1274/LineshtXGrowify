# core/workflow_manager.py - FIXED: Paragraph tag wraps entire content
import streamlit as st
from helpers.column_mapper import ColumnMapper
from helpers.description_generator import DescriptionGenerator

class WorkflowManager:
    """Enhanced workflow manager with step-based processing and dynamic description builder"""
    
    def __init__(self):
        self.column_mapper = ColumnMapper()
        self.description_generator = DescriptionGenerator()
    
    def execute_file_upload(self, ui, file_handler):
        """Step 1: Enhanced file upload with metrics and preview"""
        uploaded_file = ui.render_file_upload()
        
        if not uploaded_file:
            st.info("Please upload a CSV or Excel file to get started")
            return False
        
        try:
            df_raw = file_handler.load_file(uploaded_file)
            if df_raw.empty:
                st.error("The uploaded file is empty or could not be read")
                return False
            
            # Store raw data and show enhanced metrics
            st.session_state.df_raw = df_raw
            ui.show_file_metrics(df_raw)
            return True
            
        except Exception as e:
            st.error(f"Error loading file: {str(e)}")
            return False
    
    def execute_column_mapping_enhanced(self, ui, session):
        """Step 2: Enhanced column mapping with complete Shopify fields and editable interface"""
        df_raw = st.session_state.df_raw
        if df_raw is None:
            st.error("No data loaded. Please go back to step 1.")
            return False
        
        try:
            # Perform intelligent column mapping if not already done
            if 'mapping_result' not in st.session_state:
                st.session_state.mapping_result = self.column_mapper.analyze_columns(df_raw)
            
            mapping_result = st.session_state.mapping_result
            
            # Show enhanced mapping interface with all Shopify fields
            final_mapping = ui.render_enhanced_column_mapping(df_raw, mapping_result)
            
            # Clean up empty mappings (remove fields with no column selected)
            cleaned_mapping = {k: v for k, v in final_mapping.items() if v and v.strip()}
            
            # Store mapping in session
            session.store_mappings(cleaned_mapping)
            
            # Show current mapping summary for user confirmation
            if cleaned_mapping:
                with st.expander("📋 Current Mapping Summary", expanded=False):
                    st.write("**Active mappings:**")
                    for shopify_field, user_column in cleaned_mapping.items():
                        st.write(f"• **{shopify_field}** → {user_column}")
            
            # Auto-confirm mapping (user can always go back to modify)
            session.set_mapping_complete(True)
            return True
            
        except Exception as e:
            st.error(f"Error in column mapping: {str(e)}")
            return False
    
    def execute_description_builder(self, ui, session):
        """Step 3: Dynamic description builder"""
        df_raw = session.get('df_raw')
        if df_raw is None:
            st.error("No data loaded.")
            return False
        
        try:
            column_mapping = session.get_mappings()
            
            # Render description builder interface
            description_elements = ui.render_description_builder(df_raw, column_mapping)
            
            # Store description elements in session
            session.set_description_elements(description_elements)
            
            return True
            
        except Exception as e:
            st.error(f"Error in description builder: {str(e)}")
            return False
    
    def execute_data_processing(self, ui, data_processor, session):
        """Process data with confirmed mappings and description elements"""
        try:
            df_raw = st.session_state.df_raw
            column_mapping = session.get_mappings()
            description_elements = session.get_description_elements()
            config = session.get_config()
            
            # Generate enhanced descriptions for all rows
            if description_elements:
                sorted_elements = sorted([elem for elem in description_elements if elem.get('column')], 
                                       key=lambda x: x.get('order', 0))
                
                df_raw['enhanced_description'] = df_raw.apply(
                    lambda row: self._generate_description_html(sorted_elements, row),
                    axis=1
                )
            
            # Process variants and inventory
            processed_df = data_processor.process_data(df_raw, column_mapping, config)
            
            # Store processed data
            session.set('processed_data', processed_df)
            
            return True
            
        except Exception as e:
            st.error(f"Error processing data: {str(e)}")
            return False
    
    def execute_ai_processing(self, ui, ai_service, session):
        """Step 4: AI enhancement (if enabled)"""
        config = session.get_config()
        
        if config['mode'] == "Default template (no AI)" or not ai_service.is_enabled():
            return True  # Skip AI processing
        
        ui.render_step_header("AI Enhancement")
        
        try:
            # First ensure data is processed
            if not self.execute_data_processing(ui, None, session):
                return False
            
            processed_df = session.get('processed_data')
            column_mapping = session.get_mappings()
            
            # Process with AI
            enhanced_df = ai_service.process_descriptions(processed_df, column_mapping, config['mode'])
            session.set('processed_data', enhanced_df)
            
            return True
            
        except Exception as e:
            st.error(f"AI processing failed: {str(e)}")
            st.warning("Continuing with original descriptions...")
            return True  # Continue even if AI fails
    
    def execute_inventory_management(self, ui, data_processor, session):
        """Step 5: Inventory management interface - clean main screen, all config in sidebar"""
        try:
            # Ensure data is processed first
            if session.get('processed_data') is None:
                if not self.execute_data_processing(ui, data_processor, session):
                    return False
            
            processed_df = session.get('processed_data')
            column_mapping = session.get_mappings()
            config = session.get_config()
            
            # Initialize variant management
            data_processor.initialize_variants(processed_df, column_mapping, config)
            
            # Only show variant editor on main screen (no config options)
            st.markdown("### 📋 Variant Quantity & Price Editor")
            st.info("💡 Use the sidebar (⚙️ Configuration) to manage bulk settings, surcharges, and defaults. Edit individual variants below.")
            
            ui.render_variant_editor(session.get_variants())
            
            return True
            
        except Exception as e:
            st.error(f"Error in inventory management: {str(e)}")
            return False
    
    def execute_csv_generation(self, ui, data_processor, session):
        """Step 6: Generate final Shopify CSV"""
        ui.render_step_header("Generate Shopify CSV")
        
        try:
            # Ensure data is processed
            if session.get('processed_data') is None:
                if not self.execute_data_processing(ui, data_processor, session):
                    return False
            
            processed_df = session.get('processed_data')
            column_mapping = session.get_mappings()
            column_descriptions = session.get_descriptions()
            description_elements = session.get_description_elements()
            config = session.get_config()
            
            # Apply enhanced descriptions if not already applied
            if 'enhanced_description' not in processed_df.columns and description_elements:
                sorted_elements = sorted([elem for elem in description_elements if elem.get('column')], 
                                       key=lambda x: x.get('order', 0))
                
                processed_df['enhanced_description'] = processed_df.apply(
                    lambda row: self._generate_description_html(sorted_elements, row),
                    axis=1
                )
            
            # For backward compatibility, also apply traditional descriptions
            enhanced_df = self.description_generator.apply_enhanced_descriptions(
                processed_df, column_mapping, column_descriptions
            )
            
            # Generate final CSV
            shopify_csv = data_processor.generate_shopify_csv(
                enhanced_df, column_mapping, config
            )
            
            if shopify_csv.empty:
                st.error("Failed to generate CSV - no data produced")
                return False
            
            # Show results and download
            ui.show_final_statistics(shopify_csv)
            ui.show_tabbed_results(shopify_csv)
            ui.render_download_section(shopify_csv)
            
            return True
            
        except Exception as e:
            st.error(f"Error generating final CSV: {str(e)}")
            return False
    
    def _generate_description_html(self, elements, row):
        """FIXED: Wrap entire content in paragraph tag, apply user tags to labels only"""
        html_parts = []
        
        for element in elements:
            column = element.get('column', '')
            label = element.get('label', '')
            html_tag = element.get('html_tag', 'p')
            
            if column and column in row.index:
                value = self._clean_value(row[column])
                if value:
                    if label and label.strip():
                        # FIXED: Apply user tag to label, add value after
                        if html_tag == 'none':
                            # No tag - just label and value
                            html_parts.append(f"{label}: {value}")
                        elif html_tag == 'br':
                            # Line break after
                            html_parts.append(f"{label}: {value}<br>")
                        elif html_tag == 'li':
                            # List item wraps everything
                            html_parts.append(f"<li>{label}: {value}</li>")
                        elif html_tag == 'p':
                            # FIXED: Paragraph wraps the entire label+value together
                            html_parts.append(f"<p>{label}: {value}</p>")
                        else:
                            # Other tags wrap label only, value follows
                            html_parts.append(f"<p><{html_tag}>{label} : </{html_tag}> {value}</p>")
                    else:
                        # No label - just value with tag
                        if html_tag == 'none':
                            html_parts.append(value)
                        elif html_tag == 'br':
                            html_parts.append(f"{value}<br>")
                        elif html_tag == 'li':
                            html_parts.append(f"<li>{value}</li>")
                        elif html_tag == 'p':
                            html_parts.append(f"<p>{value}</p>")
                        else:
                            html_parts.append(f"<p><{html_tag}>{value}</{html_tag}></p>")
        
        return " ".join(html_parts)
    
    def _clean_value(self, value):
        """Clean value for HTML generation"""
        import pandas as pd
        if pd.isna(value) or str(value).strip() == '':
            return ""
        return str(value).strip()
    
    # Legacy methods for backward compatibility
    def execute_column_mapping(self, ui, session):
        """Legacy column mapping method"""
        return self.execute_column_mapping_enhanced(ui, session)
    
    def execute_data_processing_legacy(self, ui, data_processor, session):
        """Legacy data processing without description elements"""
        try:
            df_raw = st.session_state.df_raw
            column_mapping = session.get_mappings()
            config = session.get_config()
            
            # Process variants and inventory
            processed_df = data_processor.process_data(df_raw, column_mapping, config)
            
            # Store processed data
            session.set('processed_data', processed_df)
            ui.show_data_preview(processed_df, column_mapping)
            
            st.success(f"Processed {len(processed_df)} product variants")
            return True
            
        except Exception as e:
            st.error(f"Error processing data: {str(e)}")
            return False