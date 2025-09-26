# services/ai_service.py - Simplified AI processing service
import os
import time
import streamlit as st
import google.generativeai as genai
from helpers.utils import get_column_value, clean_value

class AIService:
    """Clean AI service with focused responsibilities"""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize Gemini model"""
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('models/gemini-2.5-flash')
            except Exception as e:
                st.warning(f"AI initialization failed: {e}")
                self.model = None
    
    def is_enabled(self):
        """Check if AI service is available"""
        return self.model is not None
    
    def process_descriptions(self, df, column_mapping, mode):
        """Process descriptions with AI enhancement"""
        if not self.is_enabled():
            return df
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        custom_descs, all_tags = [], []
        
        with st.spinner("AI is enhancing your descriptions..."):
            for i, (_, row) in enumerate(df.iterrows()):
                title = get_column_value(row, column_mapping, 'title', 'Unknown')
                status_text.text(f"Processing {i+1}/{len(df)}: {str(title)[:30]}...")
                
                original_desc = clean_value(get_column_value(row, column_mapping, 'description', ""))
                
                if mode == "Simple mode (first sentence + tags)":
                    desc, tags = self._process_simple_mode(original_desc)
                elif mode == "Full AI mode (custom description + tags)":
                    desc, tags = self._process_full_ai_mode(original_desc)
                else:
                    desc, tags = original_desc, ""
                
                custom_descs.append(desc)
                all_tags.append(tags)
                
                progress_bar.progress((i + 1) / len(df))
                time.sleep(0.1)
        
        status_text.text("AI processing complete!")
        
        df["custom_description"] = custom_descs
        df["ai_tags"] = all_tags
        
        return df
    
    def _process_simple_mode(self, text):
        """Extract first sentence and generate tags"""
        if not text:
            return "", ""
        
        first_sentence = text.split(".", 1)[0].strip()
        tags = self._generate_tags(first_sentence)
        
        return first_sentence, tags
    
    def _process_full_ai_mode(self, text):
        """Generate enhanced description and tags"""
        if not text:
            return "", ""
        
        prompt = (
            "You are a Shopify copywriter. Rewrite this product description to be engaging and clear.\n"
            "Then provide 5 comma-separated tags.\n\n"
            f"Original: {text}\n\n"
            "Respond with:\n"
            "Line 1: Enhanced description\n"
            "Line 2: tag1,tag2,tag3,tag4,tag5"
        )
        
        try:
            response = self.model.generate_content(prompt)
            result = (response.text or "").strip()
            
            lines = result.split('\n', 1)
            if len(lines) >= 2:
                return lines[0].strip(), lines[1].strip()
            else:
                return result, ""
        except Exception as e:
            st.warning(f"AI processing failed: {e}")
            return text, ""
    
    def _generate_tags(self, text):
        """Generate tags from text"""
        if not text:
            return ""
        
        prompt = (
            "Extract 5 relevant product tags from this text.\n"
            "Return only tags as comma-separated list.\n\n"
            f"Text: {text}\n\n"
            "Tags:"
        )
        
        try:
            response = self.model.generate_content(prompt)
            return (response.text or "").strip()
        except Exception as e:
            return ""