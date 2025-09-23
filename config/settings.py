# config/settings.py - User-configurable settings and defaults
"""
Default settings and configuration that users might want to modify
These are the "business rules" that can change based on requirements
"""

class AppSettings:
    """Application settings that can be customized"""
    
    # Default values for new users
    DEFAULT_VENDOR_NAME = "YourBrandName"
    DEFAULT_INVENTORY_POLICY = "deny"  # or "continue"
    DEFAULT_QUANTITY = 10
    DEFAULT_COMPARE_PRICE = 0.0
    
    # UI behavior settings
    SHOW_ADVANCED_OPTIONS = True
    ENABLE_SPREADSHEET_EDITOR = True
    MAX_PRODUCTS_EXPANDED = 3  # Auto-expand first N products in inventory mgmt
    
    # Processing settings
    AI_PROCESSING_DELAY = 0.1  # seconds between AI requests
    ENABLE_PROGRESS_BARS = True
    AUTO_SAVE_SESSION = True
    
    # Data validation settings
    WARN_ON_ZERO_PRICES = True
    REQUIRE_SKU = False
    VALIDATE_SIZE_FORMAT = True
    
    # Export settings
    INCLUDE_OPTIONAL_SHOPIFY_COLUMNS = True
    CLEAN_HTML_OUTPUT = True
    SORT_VARIANTS_BY_SIZE = True
    
    @classmethod
    def get_default_config(cls):
        """Get default configuration dictionary"""
        return {
            'vendor_name': cls.DEFAULT_VENDOR_NAME,
            'inventory_policy': cls.DEFAULT_INVENTORY_POLICY,
            'default_qty': cls.DEFAULT_QUANTITY,
            'default_compare_price': cls.DEFAULT_COMPARE_PRICE,
            'enable_surcharge': False,
            'surcharge_rules': {},
            'bulk_qty_mode': False,
            'bulk_compare_price_mode': False,
            'mode': 'Default template (no AI)'
        }
    
    @classmethod
    def get_inventory_policies(cls):
        """Get available inventory policy options"""
        return {
            'deny': 'Stop sales when out of stock',
            'continue': 'Allow sales when out of stock'
        }