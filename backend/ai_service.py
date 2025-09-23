# backend/ai_service.py - AI processing service
import os
import time
import streamlit as st
import google.generativeai as genai
from helpers.utils import get_column_value, clean_value

class AIService:
    def __init__(self):
        """Initialize AI service with API key validation"""
        self.api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize Gemini model if API key is available"""
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('models/gemini-2.5-flash')
            except Exception as e:
                st.warning(f"Failed to initialize AI model: {e}")
                self.model = None
    
    def is_enabled(self):
        """Check if AI service is available"""
        return self.model is not None
    
    def process_descriptions_batch(self, df, column_mapping, mode):
        """Process product descriptions in batch with progress tracking"""
        n = len(df)
        custom_descs, all_tags = [], []
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with st.spinner("🔮 AI is working its magic..."):
            for i, (_, row) in enumerate(df.iterrows()):
                # Get title for progress display
                title = get_column_value(row, column_mapping, 'title', 'Unknown')
                if title == 'Unknown' or not title:
                    title = 'Unknown Product'
                    
                status_text.text(f"Processing product {i+1}/{n}: {str(title)[:30]}...")
                
                # Process based on mode
                original_desc = clean_value(get_column_value(row, column_mapping, 'description', ""))
                
                if mode == "Simple mode (first sentence + tags)":
                    desc, tags = self._process_simple_mode(original_desc)
                elif mode == "Full AI mode (custom description + tags)":
                    desc, tags = self._process_full_ai_mode(original_desc)
                else:
                    desc, tags = original_desc, ""
                
                custom_descs.append(desc)
                all_tags.append(tags)
                
                # Update progress
                progress_bar.progress((i + 1) / n)
                time.sleep(0.1)  # Rate limiting
        
        status_text.text("✅ AI processing complete!")
        
        # Add results to dataframe
        df["custom_description"] = custom_descs
        df["ai_tags"] = all_tags
        
        return df
    
    def _process_simple_mode(self, text):
        """Process text in simple mode - first sentence + tags"""
        if not self.is_enabled() or not text:
            return text, ""
        
        # Extract first sentence
        first_sentence = text.split(".", 1)[0].strip()
        if not first_sentence:
            first_sentence = text
        
        # Generate tags
        tags = self._generate_tags_only(first_sentence)
        
        return first_sentence, tags
    
    def _process_full_ai_mode(self, text):
        """Process text in full AI mode - custom description + tags"""
        if not self.is_enabled() or not text:
            return text, ""
        
        return self._refine_and_tag(text)
    
    def _generate_tags_only(self, text):
        """Generate tags from text using AI"""
        if not self.is_enabled() or not text:
            return ""
        
        prompt = (
            "Extract exactly 5 relevant product tags from this text. "
            "Return only the tags as a comma-separated list with no extra text.\n\n"
            f"Text: {text}\n\n"
            "Tags:"
        )
        
        try:
            response = self.model.generate_content(prompt)
            return (response.text or "").strip()
        except Exception as e:
            st.warning(f"AI tag generation failed: {e}")
            return ""
    
    def _refine_and_tag(self, text):
        """Generate refined description and tags"""
        if not self.is_enabled() or not text:
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
            response = self.model.generate_content(prompt)
            result = (response.text or "").strip()
            
            # Split response into description and tags
            lines = result.split('\n', 1)
            if len(lines) >= 2:
                description = lines[0].strip()
                tags = lines[1].strip()
                return description, tags
            else:
                return result, ""
                
        except Exception as e:
            st.warning(f"AI processing failed: {e}")
            return text, ""