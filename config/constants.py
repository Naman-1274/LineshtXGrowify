# config/constants.py - Application constants that rarely change
"""
Static configuration values and constants for the Shopify CSV Builder
These are values that define the structure and behavior of the app
"""

# Shopify CSV column structure - this never changes
SHOPIFY_REQUIRED_COLUMNS = [
    "Handle", "Title", "Body (HTML)", "Vendor", "Product Category", "Type", "Tags", 
    "Published", "Option1 Name", "Option1 Value", "Option2 Name", "Option2 Value", 
    "Option3 Name", "Option3 Value", "Variant SKU", "Variant Grams", 
    "Variant Inventory Tracker", "Variant Inventory Qty", "Variant Inventory Policy", 
    "Variant Fulfillment Service", "Variant Compare At Price", "Variant Price", 
    "Variant Requires Shipping", "Variant Taxable"
]

# Additional Shopify columns for completeness
SHOPIFY_OPTIONAL_COLUMNS = [
    "Image Src", "Image Position", "Image Alt Text", "Gift Card", "SEO Title", 
    "SEO Description", "Google Shopping / Google Product Category", 
    "Google Shopping / Gender", "Google Shopping / Age Group", "Google Shopping / MPN", 
    "Google Shopping / AdWords Grouping", "Google Shopping / AdWords Labels", 
    "Google Shopping / Condition", "Google Shopping / Custom Product", 
    "Google Shopping / Custom Label 0", "Google Shopping / Custom Label 1", 
    "Google Shopping / Custom Label 2", "Google Shopping / Custom Label 3", 
    "Google Shopping / Custom Label 4", "Variant Image", "Variant Weight Unit", 
    "Variant Tax Code", "Cost per item", "Status"
]

# Size ordering for proper sorting - this is business logic that rarely changes
STANDARD_SIZE_ORDER = [
    'XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', 
    '2XL', '3XL', '4XL', '5XL'
]

# AI processing modes - these define app capabilities
AI_PROCESSING_MODES = [
    "Default template (no AI)",
    "Simple mode (first sentence + tags)",
    "Full AI mode (custom description + tags)"
]

# Column name variations for case-insensitive matching
# This mapping defines what input columns we can recognize
COLUMN_MAPPING_VARIANTS = {
    'title': [
        'title', 'product_title', 'product title', 'name', 
        'product_name', 'product name'
    ],
    'description': [
        'description', 'product_description', 'product description', 'desc'
    ],
    'colour': [
        'colour', 'color', 'colors', 'colours'
    ],
    'product code': [
        'product code', 'product_code', 'sku', 'product_sku', 
        'item_code', 'item code'
    ],
    'product category': [
        'product category', 'product_category', 'category', 'product_type'
    ],
    'type': [
        'type', 'product_type', 'product type'
    ],
    'published': [
        'published', 'status', 'active', 'publish_status', 'publish status'
    ],
    'size': [
        'size', 'sizes', 'variant_size', 'variant size'
    ],
    'no of components': [
        'no of components', 'no_of_components', 'components', 
        'number_of_components', 'component_count'
    ],
    'fabric': [
        'fabric', 'material', 'fabric_type', 'fabric type'
    ],
    'variant price': [
        'variant price', 'variant_price', 'price', 'unit_price', 
        'unit price', 'cost'
    ],
    'variant compare at price': [
        'variant compare at price', 'variant_compare_at_price', 
        'compare_price', 'compare price', 'compare at price', 
        'compare_at_price', 'original_price', 'original price'
    ],
    'celebs name': [
        'celebs name', 'celebs_name', 'celebrity_name', 'celebrity name', 
        'celeb_name', 'celeb name'
    ],
    'fit': [
        'fit', 'fitting', 'size_fit', 'size fit'
    ],
    'sizes info': [
        'sizes info', 'sizes_info', 'size_info', 'size info'
    ],
    'delivery time': [
        'delivery time', 'delivery_time', 'shipping_time', 'shipping time'
    ],
    'wash care': [
        'wash care', 'wash_care', 'care_instructions', 'care instructions'
    ],
    'technique used': [
        'technique used', 'technique_used', 'manufacturing_technique', 
        'manufacturing technique'
    ],
    'embroidery details': [
        'embroidery details', 'embroidery_details', 'embroidery', 
        'embroidery_info'
    ]
}

# File processing limits
MAX_FILE_SIZE_MB = 50
SUPPORTED_FILE_TYPES = ['csv', 'xlsx']
MAX_ROWS_PER_BATCH = 1000

# AI service configuration
GEMINI_MODEL_NAME = 'models/gemini-2.5-flash'
AI_REQUEST_TIMEOUT = 30  # seconds
AI_RETRY_ATTEMPTS = 3