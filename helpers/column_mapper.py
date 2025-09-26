# helpers/column_mapper.py - Enhanced column mapping with intelligent detection
import pandas as pd
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple
from difflib import SequenceMatcher

@dataclass
class MappingResult:
    """Container for mapping analysis results"""
    base_mapping: Dict[str, str]
    unmapped_columns: List[str]
    confidence_scores: Dict[str, float]

class ColumnMapper:
    """Enhanced column mapping with multiple detection methods"""
    
    def __init__(self):
        self.standard_variants = self._get_column_variants()
        self.standard_fields = list(self.standard_variants.keys())
    
    def analyze_columns(self, df: pd.DataFrame) -> MappingResult:
        """Perform complete column analysis and mapping"""
        # Step 1: Exact matching (case-insensitive)
        base_mapping = self._exact_match(df)
        
        # Step 2: Find unmapped columns
        mapped_columns = set(base_mapping.values())
        unmapped_columns = [col for col in df.columns if col not in mapped_columns]
        
        # Step 3: Fuzzy matching for unmapped columns
        fuzzy_mapping, fuzzy_confidence = self._fuzzy_match(unmapped_columns, base_mapping)
        
        # Step 4: Content analysis for remaining columns
        remaining_unmapped = [col for col in unmapped_columns if col not in fuzzy_mapping.values()]
        content_mapping, content_confidence = self._content_analysis(df, remaining_unmapped, base_mapping)
        
        # Step 5: Combine results
        final_mapping = base_mapping.copy()
        final_mapping.update(fuzzy_mapping)
        final_mapping.update(content_mapping)
        
        # Calculate confidence scores
        confidence_scores = {}
        for standard_name, actual_column in base_mapping.items():
            confidence_scores[actual_column] = 1.0  # Exact matches = 100%
        confidence_scores.update(fuzzy_confidence)
        confidence_scores.update(content_confidence)
        
        # Final unmapped columns
        final_unmapped = [col for col in df.columns if col not in final_mapping.values()]
        
        return MappingResult(final_mapping, final_unmapped, confidence_scores)
    
    def _exact_match(self, df: pd.DataFrame) -> Dict[str, str]:
        """Perform exact case-insensitive matching"""
        mapping = {}
        actual_columns_lower = {col.lower().strip(): col for col in df.columns}
        
        for standard_name, variants in self.standard_variants.items():
            for variant in variants:
                if variant.lower() in actual_columns_lower:
                    mapping[standard_name] = actual_columns_lower[variant.lower()]
                    break
        
        return mapping
    
    def _fuzzy_match(self, unmapped_columns: List[str], existing_mapping: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Use fuzzy string matching for similar column names"""
        fuzzy_mapping = {}
        confidence_scores = {}
        
        for col in unmapped_columns:
            best_match = self._find_best_fuzzy_match(col, existing_mapping)
            if best_match:
                standard_name, confidence = best_match
                fuzzy_mapping[standard_name] = col
                confidence_scores[col] = confidence
        
        return fuzzy_mapping, confidence_scores
    
    def _find_best_fuzzy_match(self, column: str, existing_mapping: Dict[str, str]) -> Tuple[str, float]:
        """Find best fuzzy match for a column"""
        best_score = 0
        best_standard = None
        
        for standard_name, variants in self.standard_variants.items():
            if standard_name in existing_mapping:
                continue
            
            for variant in variants:
                similarity = self._calculate_similarity(column.lower(), variant.lower())
                if similarity > best_score and similarity > 0.7:
                    best_score = similarity
                    best_standard = standard_name
        
        return (best_standard, best_score) if best_standard else None
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        # Clean strings for better matching
        str1_clean = re.sub(r'[_\-\s]+', '', str1)
        str2_clean = re.sub(r'[_\-\s]+', '', str2)
        
        # Base similarity
        similarity = SequenceMatcher(None, str1_clean, str2_clean).ratio()
        
        # Boost if one contains the other
        if str2_clean in str1_clean or str1_clean in str2_clean:
            similarity = max(similarity, 0.8)
        
        return similarity
    
    def _content_analysis(self, df: pd.DataFrame, unmapped_columns: List[str], 
                         existing_mapping: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Analyze column content to determine type"""
        content_mapping = {}
        confidence_scores = {}
        
        for col in unmapped_columns:
            sample_values = df[col].dropna().astype(str).head(10).tolist()
            if not sample_values:
                continue
            
            detected_type, confidence = self._detect_column_type(sample_values, col)
            
            if detected_type and confidence > 0.6 and detected_type not in existing_mapping:
                content_mapping[detected_type] = col
                confidence_scores[col] = confidence
        
        return content_mapping, confidence_scores
    
    def _detect_column_type(self, sample_values: List[str], column_name: str) -> Tuple[str, float]:
        """Detect column type based on content analysis"""
        values_lower = [str(v).lower().strip() for v in sample_values if str(v).strip()]
        
        # Price detection
        if self._is_price_column(values_lower) > 0.7:
            return 'variant price', 0.8
        
        # Status detection
        if self._is_status_column(values_lower) > 0.6:
            return 'published', 0.7
        
        # Size detection
        if self._is_size_column(values_lower) > 0.6:
            return 'size', 0.7
        
        # Color detection
        if self._is_color_column(values_lower) > 0.6:
            return 'colour', 0.7
        
        # Category detection
        if self._is_category_column(values_lower) > 0.5:
            return 'product category', 0.6
        
        # SKU/Code detection
        if self._is_code_column(values_lower, column_name.lower()) > 0.7:
            return 'product code', 0.8
        
        return None, 0
    
    def _is_price_column(self, values: List[str]) -> float:
        """Check if values look like prices"""
        price_count = 0
        for value in values:
            clean_value = re.sub(r'[₹$€£,\s]', '', str(value))
            try:
                num = float(clean_value)
                if 0 < num < 100000:
                    price_count += 1
            except ValueError:
                continue
        return price_count / len(values) if values else 0
    
    def _is_status_column(self, values: List[str]) -> float:
        """Check if values are status indicators"""
        status_words = {'active', 'inactive', 'draft', 'published', 'unpublished', 'true', 'false', 'yes', 'no'}
        status_count = sum(1 for v in values if v in status_words)
        return status_count / len(values) if values else 0
    
    def _is_size_column(self, values: List[str]) -> float:
        """Check if values are clothing sizes"""
        size_patterns = [
            r'\b(xs|s|m|l|xl|xxl|xxxl)\b',
            r'\b\d{1,2}\b',
            r'\b(small|medium|large)\b',
            r'\b\d{1,2}-\d+\b'
        ]
        size_count = 0
        for value in values:
            if any(re.search(pattern, value) for pattern in size_patterns):
                size_count += 1
        return size_count / len(values) if values else 0
    
    def _is_color_column(self, values: List[str]) -> float:
        """Check if values are colors"""
        color_words = {
            'red', 'blue', 'green', 'yellow', 'black', 'white', 'pink', 'purple',
            'orange', 'brown', 'gray', 'grey', 'navy', 'maroon', 'teal', 'cyan'
        }
        color_count = sum(1 for v in values if any(color in v for color in color_words))
        return color_count / len(values) if values else 0
    
    def _is_category_column(self, values: List[str]) -> float:
        """Check if values are product categories"""
        category_words = {
            'shirt', 'dress', 'pants', 'jeans', 'jacket', 'shoes', 'bag',
            'jewelry', 'clothing', 'apparel', 'accessories', 'footwear'
        }
        category_count = sum(1 for v in values if any(cat in v for cat in category_words))
        return category_count / len(values) if values else 0
    
    def _is_code_column(self, values: List[str], column_name: str) -> float:
        """Check if values are product codes/SKUs"""
        name_hints = ['sku', 'code', 'id', 'number', 'ref']
        name_bonus = 0.3 if any(hint in column_name for hint in name_hints) else 0
        
        code_count = 0
        for value in values:
            if re.match(r'^[A-Za-z0-9_-]+$', value.strip()) and len(value.strip()) > 2:
                code_count += 1
        
        base_score = code_count / len(values) if values else 0
        return min(1.0, base_score + name_bonus)
    
    
    def _get_column_variants(self) -> Dict[str, List[str]]:
        """Get all column name variations for mapping - COMPLETE SHOPIFY COLUMNS"""
        return {
            # Core Product Fields
            'Handle': ['handle', 'product_handle', 'product handle'],
            'Title': ['title', 'product_title', 'product title', 'name', 'product_name', 'product name'],
            'Body (HTML)': ['body (html)', 'body html', 'description', 'product_description', 'product description', 'desc', 'body'],
            'Vendor': ['vendor', 'brand', 'manufacturer', 'supplier'],
            'Product Category': ['product category', 'product_category', 'category', 'product_type'],
            'Type': ['type', 'product_type', 'product type'],
            'Tags': ['tags', 'product_tags', 'keywords'],
            'Published': ['published', 'status', 'active', 'publish_status', 'publish status'],
            
            # Option Fields
            'Option1 Name': ['option1 name', 'option1_name', 'option 1 name'],
            'Option1 Value': ['option1 value', 'option1_value', 'option 1 value', 'size', 'sizes'],
            'Option2 Name': ['option2 name', 'option2_name', 'option 2 name'],
            'Option2 Value': ['option2 value', 'option2_value', 'option 2 value', 'colour', 'color', 'colors', 'colours'],
            'Option3 Name': ['option3 name', 'option3_name', 'option 3 name'],
            'Option3 Value': ['option3 value', 'option3_value', 'option 3 value'],
            
            # Variant Fields - CRITICAL MISSING FIELDS
            'Variant SKU': ['variant sku', 'variant_sku', 'sku', 'product_sku', 'product sku', 'product code', 'product_code', 'item_code', 'item code', 'Product code', 'Porduct Code'],
            'Variant Grams': ['variant grams', 'variant_grams', 'weight_grams', 'weight grams'],
            'Variant Inventory Tracker': ['variant inventory tracker', 'variant_inventory_tracker', 'inventory tracker', 'inventory_tracker'],
            'Variant Inventory Qty': ['variant inventory qty', 'variant_inventory_qty', 'inventory qty', 'inventory_qty', 'quantity', 'stock', 'stock_quantity'],
            'Variant Inventory Policy': ['variant inventory policy', 'variant_inventory_policy', 'inventory policy', 'inventory_policy'],
            'Variant Fulfillment Service': ['variant fulfillment service', 'variant_fulfillment_service', 'fulfillment service', 'fulfillment_service'],
            'Variant Price': ['variant price', 'variant_price', 'price', 'unit_price', 'unit price', 'cost', 'selling_price'],
            'Variant Compare At Price': ['variant compare at price', 'variant_compare_at_price', 'compare price', 'compare_price', 'compare at price', 'compare_at_price', 'original_price', 'original price', 'mrp'],
            'Variant Requires Shipping': ['variant requires shipping', 'variant_requires_shipping', 'requires shipping', 'requires_shipping', 'shipping_required'],
            'Variant Taxable': ['variant taxable', 'variant_taxable', 'taxable', 'tax_applicable'],
            'Variant Barcode': ['variant barcode', 'variant_barcode', 'barcode', 'upc', 'ean'],
            'Variant Image': ['variant image', 'variant_image', 'image', 'product_image'],
            'Variant Weight Unit': ['variant weight unit', 'variant_weight_unit', 'weight unit', 'weight_unit'],
            'Variant Weight': ['variant weight', 'variant_weight', 'weight'],
            
            # Image Fields
            'Image Src': ['image src', 'image_src', 'image url', 'image_url', 'image', 'product_image'],
            'Image Position': ['image position', 'image_position'],
            'Image Alt Text': ['image alt text', 'image_alt_text', 'alt text', 'alt_text'],
            
            # Additional Product Fields
            'Gift Card': ['gift card', 'gift_card'],
            'SEO Title': ['seo title', 'seo_title', 'meta title', 'meta_title'],
            'SEO Description': ['seo description', 'seo_description', 'meta description', 'meta_description'],
            
            # Google Shopping Fields
            'Google Shopping / Google Product Category': ['google shopping / google product category', 'google product category', 'google_product_category'],
            'Google Shopping / Gender': ['google shopping / gender', 'gender', 'target_gender'],
            'Google Shopping / Age Group': ['google shopping / age group', 'age group', 'age_group'],
            'Google Shopping / MPN': ['google shopping / mpn', 'mpn', 'manufacturer_part_number'],
            'Google Shopping / AdWords Grouping': ['google shopping / adwords grouping', 'adwords grouping', 'adwords_grouping'],
            'Google Shopping / AdWords Labels': ['google shopping / adwords labels', 'adwords labels', 'adwords_labels'],
            'Google Shopping / Condition': ['google shopping / condition', 'condition', 'product_condition'],
            'Google Shopping / Custom Product': ['google shopping / custom product', 'custom product', 'custom_product'],
            'Google Shopping / Custom Label 0': ['google shopping / custom label 0', 'custom label 0', 'custom_label_0'],
            'Google Shopping / Custom Label 1': ['google shopping / custom label 1', 'custom label 1', 'custom_label_1'],
            'Google Shopping / Custom Label 2': ['google shopping / custom label 2', 'custom label 2', 'custom_label_2'],
            'Google Shopping / Custom Label 3': ['google shopping / custom label 3', 'custom label 3', 'custom_label_3'],
            'Google Shopping / Custom Label 4': ['google shopping / custom label 4', 'custom label 4', 'custom_label_4'],
            
            # Cost and Pricing
            'Cost per item': ['cost per item', 'cost_per_item', 'cost', 'wholesale_price', 'wholesale price'],
            'Price / International': ['price / international', 'price_international', 'international_price'],
            'Compare At Price / International': ['compare at price / international', 'compare_at_price_international', 'international_compare_price'],
            'Status': ['status', 'product_status', 'active', 'draft', 'archived'],
            
            # Custom Business Fields (your existing ones)
            'no of components': ['no of components', 'no_of_components', 'components', 'number_of_components', 'component_count'],
            'fabric': ['fabric', 'material', 'fabric_type', 'fabric type'],
            'celebs name': ['celebs name', 'celebs_name', 'celebrity_name', 'celebrity name'],
            'fit': ['fit', 'fitting', 'size_fit', 'size fit'],
            'sizes info': ['sizes info', 'sizes_info', 'size_info', 'size info'],
            'delivery time': ['delivery time', 'delivery_time', 'shipping_time', 'shipping time'],
            'wash care': ['wash care', 'wash_care', 'care_instructions', 'care instructions'],
            'technique used': ['technique used', 'technique_used', 'manufacturing_technique'],
            'embroidery details': ['embroidery details', 'embroidery_details', 'embroidery']
        }